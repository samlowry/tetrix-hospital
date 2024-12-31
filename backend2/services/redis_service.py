from redis.asyncio import Redis, ConnectionPool
from datetime import timedelta, datetime
import json
import logging
from typing import Optional, Any, Dict
from enum import Enum
from core.cache import cache_permanent, CacheKeys, Cache
from core.logger import logger

class UserStatus(Enum):
    """Enum representing different states of user registration"""
    WAITING_WALLET = "waiting_wallet"  # User is waiting to connect their wallet
    WAITING_INVITE = "waiting_invite"  # User needs to enter an invite code
    REGISTERED = "registered"          # User has completed registration

# Dictionary of Redis key patterns used throughout the application
REDIS_KEYS = {
    'bot': 'bot',                          # Base key for bot-related data
    'bot_state': 'bot:state',              # Stores the current state of the bot
    'bot_data': 'bot:data',                # General bot data storage
    'webhook_url': 'bot:webhook_url',      # URL for bot webhook
    'user_data': 'bot:user_data',          # User-specific data storage
    'chat_data': 'bot:chat_data',          # Chat-specific data storage
    'callback_data': 'bot:callback_data',   # Callback query data
    'conversations': 'bot:conversations',   # Conversation state tracking
    'user_sessions': 'user_sessions',       # Active user session data
    'initialized': 'bot:initialized',       # Bot initialization flag
    'user_status': 'user:{}:status'        # User registration status (formatted with user ID)
}

class RedisService:
    """Service class for handling Redis operations"""
    def __init__(self, redis: Redis, cache: Optional[Cache] = None):
        """
        Initialize Redis service
        Args:
            redis (Redis): Configured Redis client instance (legacy - will be removed)
            cache (Cache): Configured aiocache instance
        """
        self.redis = redis
        self.cache = cache
        self.default_ttl = timedelta(days=5)  # Default time-to-live for Redis keys

    @classmethod
    def create(cls, host: str = 'redis', port: int = 6379):
        """
        Create a new Redis service instance with configured connection pool
        Args:
            host (str): Redis host address
            port (int): Redis port number
        Returns:
            RedisService: Configured service instance
        """
        pool = ConnectionPool(
            host=host,
            port=port,
            db=0,
            decode_responses=True,  # Automatically decode responses to UTF-8
            socket_timeout=10,      # Socket timeout in seconds
            socket_connect_timeout=10,
            socket_keepalive=True,  # Keep connection alive
            health_check_interval=15,
            max_connections=100,    # Maximum number of connections in the pool
            retry_on_timeout=True   # Retry operations on timeout
        )
        redis = Redis(connection_pool=pool)
        return cls(redis)

    # Methods for handling user status
    @cache_permanent(key_pattern=CacheKeys.USER_STATUS)
    async def get_user_status(self, telegram_id: int) -> Optional[dict]:
        """
        Get the status of a user
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            Optional[dict]: User status data or None if not found
        """
        key = CacheKeys.USER_STATUS.format(telegram_id=telegram_id)
        
        if self.cache:
            status = await self.cache.get(key)
            if status is not None:
                try:
                    return json.loads(status)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode status from cache for user {telegram_id}")
        
        # Fallback to Redis
        status = await self.redis.get(key)
        if status:
            try:
                parsed = json.loads(status)
                # Cache the value for future use
                if self.cache:
                    await self.cache.set(key, status)
                return parsed
            except json.JSONDecodeError:
                logger.error(f"Failed to decode status from Redis for user {telegram_id}")
        
        return None

    async def set_user_status(self, telegram_id: int, status: dict) -> bool:
        """
        Set the status of a user
        Args:
            telegram_id (int): User's Telegram ID
            status (dict): User status data
        Returns:
            bool: True if the operation was successful
        """
        key = CacheKeys.USER_STATUS.format(telegram_id=telegram_id)
        status_json = json.dumps(status)
        
        if self.cache:
            await self.cache.set(key, status_json)
        
        return True

    async def update_user_status(self, telegram_id: int, **kwargs) -> bool:
        """
        Update specific fields of a user's status
        Args:
            telegram_id (int): User's Telegram ID
            **kwargs: Key-value pairs to update in the user status
        Returns:
            bool: True if the operation was successful
        """
        current_status = await self.get_user_status(telegram_id) or {}
        current_status.update(kwargs)
        return await self.set_user_status(telegram_id, current_status)

    async def set_status_waiting_wallet(self, telegram_id: int) -> bool:
        """
        Set the user status to waiting for wallet connection
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            bool: True if the operation was successful
        """
        status_data = {
            'status': UserStatus.WAITING_WALLET.value,
            'updated_at': datetime.utcnow().isoformat()
        }
        return await self.set_user_status(telegram_id, status_data)

    async def set_status_waiting_invite(self, telegram_id: int) -> bool:
        """
        Set the user status to waiting for an invite code
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            bool: True if the operation was successful
        """
        status_data = {
            'status': UserStatus.WAITING_INVITE.value,
            'updated_at': datetime.utcnow().isoformat()
        }
        return await self.set_user_status(telegram_id, status_data)

    async def set_status_registered(self, telegram_id: int) -> bool:
        """
        Set the user status to registered
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            bool: True if the operation was successful
        """
        status_data = {
            'status': UserStatus.REGISTERED.value,
            'updated_at': datetime.utcnow().isoformat()
        }
        return await self.set_user_status(telegram_id, status_data)

    async def get_user_status_value(self, telegram_id: int) -> Optional[str]:
        """
        Get just the status value from user status data
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            Optional[str]: User status value or None if not found
        """
        status = await self.get_user_status(telegram_id)
        return status.get('status') if status else None

    async def clear_user_data(self, telegram_id: int) -> bool:
        """
        Clear all user data from cache
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            bool: True if the operation was successful
        """
        keys = [
            CacheKeys.USER_STATUS.format(telegram_id=telegram_id),
            CacheKeys.USER_LANGUAGE.format(telegram_id=telegram_id)
        ]
        
        if self.cache:
            for key in keys:
                await self.cache.delete(key)
        
        return True

    async def health_check(self) -> dict:
        """
        Check the availability of Redis and cache
        Returns:
            dict: Status of Redis and cache services
        """
        status = {
            'redis': False,
            'cache': False
        }
        
        # Check Redis
        try:
            status['redis'] = await self.redis.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
        
        # Check cache if available
        if self.cache:
            try:
                test_key = "health_check_test"
                await self.cache.set(test_key, "test", ttl=1)
                test_value = await self.cache.get(test_key)
                status['cache'] = test_value == "test"
            except Exception as e:
                logger.error(f"Cache health check failed: {e}")
        
        return status 