from redis.asyncio import Redis, ConnectionPool
from datetime import timedelta, datetime
import json
import logging
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)

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
    def __init__(self, redis: Redis):
        """
        Initialize Redis service
        Args:
            redis (Redis): Configured Redis client instance
        """
        self.redis = redis
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
    async def get_user_status(self, telegram_id: int) -> Optional[dict]:
        """
        Get the status of a user
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            Optional[dict]: User status data or None if not found
        """
        key = REDIS_KEYS['user_status'].format(telegram_id)
        status = await self.redis.get(key)
        if status:
            try:
                return json.loads(status)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode status for user {telegram_id}")
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
        key = REDIS_KEYS['user_status'].format(telegram_id)
        await self.redis.set(key, json.dumps(status), ex=self.default_ttl)
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
        return await self.set_user_status(telegram_id, {
            'status': UserStatus.WAITING_WALLET.value,
            'updated_at': datetime.utcnow().isoformat()
        })

    async def set_status_waiting_invite(self, telegram_id: int) -> bool:
        """
        Set the user status to waiting for an invite code
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            bool: True if the operation was successful
        """
        return await self.set_user_status(telegram_id, {
            'status': UserStatus.WAITING_INVITE.value,
            'updated_at': datetime.utcnow().isoformat()
        })

    async def set_status_registered(self, telegram_id: int) -> bool:
        """
        Set the user status to registered
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            bool: True if the operation was successful
        """
        return await self.set_user_status(telegram_id, {
            'status': UserStatus.REGISTERED.value,
            'updated_at': datetime.utcnow().isoformat()
        })

    async def get_user_status_value(self, telegram_id: int) -> Optional[str]:
        """
        Get the value of a user's status
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            Optional[str]: User status value or None if not found
        """
        status = await self.get_user_status(telegram_id)
        return status.get('status') if status else None

    # Methods for handling user state
    async def get_user_state(self, telegram_id: int) -> str:
        """
        Get the current state of a user
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            str: User state or an empty string if not found
        """
        key = f"user:{telegram_id}:state"
        state = await self.redis.get(key)
        return state or ""

    async def set_user_state(self, telegram_id: int, state: str) -> bool:
        """
        Set the state of a user
        Args:
            telegram_id (int): User's Telegram ID
            state (str): User state
        Returns:
            bool: True if the operation was successful
        """
        key = f"user:{telegram_id}:state"
        await self.redis.set(key, state, ex=self.default_ttl)
        return True

    # Methods for handling user context
    async def get_context(self, telegram_id: int) -> dict:
        """
        Get the context of a user's dialog
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            dict: User context or an empty dictionary if not found
        """
        key = f"user:{telegram_id}:context"
        context = await self.redis.get(key)
        if context:
            try:
                return json.loads(context)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode context for user {telegram_id}")
        return {}

    async def update_context(self, telegram_id: int, context: dict) -> bool:
        """
        Update the context of a user's dialog
        Args:
            telegram_id (int): User's Telegram ID
            context (dict): User context
        Returns:
            bool: True if the operation was successful
        """
        key = f"user:{telegram_id}:context"
        await self.redis.set(key, json.dumps(context), ex=self.default_ttl)
        return True

    # Methods for handling bot state
    async def get_bot_state(self) -> str:
        """
        Get the current state of the bot
        Returns:
            str: Bot state or an empty string if not found
        """
        state = await self.redis.get(REDIS_KEYS['bot_state'])
        return state or ""

    async def set_bot_state(self, state: str) -> bool:
        """
        Set the state of the bot
        Args:
            state (str): Bot state
        Returns:
            bool: True if the operation was successful
        """
        await self.redis.set(REDIS_KEYS['bot_state'], state)
        return True

    async def is_bot_initialized(self) -> bool:
        """
        Check if the bot has been initialized
        Returns:
            bool: True if the bot has been initialized
        """
        return await self.redis.get(REDIS_KEYS['initialized']) == 'true'

    async def set_bot_initialized(self) -> bool:
        """
        Set the bot initialization flag
        Returns:
            bool: True if the operation was successful
        """
        await self.redis.set(REDIS_KEYS['initialized'], 'true')
        return True

    # Methods for handling user sessions
    async def get_user_session(self, user_id: int) -> dict:
        """
        Get the session data of a user
        Args:
            user_id (int): User's ID
        Returns:
            dict: User session data or an empty dictionary if not found
        """
        session = await self.redis.get(f"{REDIS_KEYS['user_sessions']}:{user_id}")
        if session:
            try:
                return json.loads(session)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode session for user {user_id}")
        return {}

    async def set_user_session(self, user_id: int, session_data: dict) -> bool:
        """
        Set the session data of a user
        Args:
            user_id (int): User's ID
            session_data (dict): User session data
        Returns:
            bool: True if the operation was successful
        """
        await self.redis.set(
            f"{REDIS_KEYS['user_sessions']}:{user_id}",
            json.dumps(session_data),
            ex=self.default_ttl
        )
        return True

    async def clear_user_data(self, telegram_id: int) -> bool:
        """
        Clear all data of a user
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            bool: True if the operation was successful
        """
        keys = [
            f"user:{telegram_id}:state",
            f"user:{telegram_id}:context",
            f"{REDIS_KEYS['user_sessions']}:{telegram_id}",
            REDIS_KEYS['user_status'].format(telegram_id)
        ]
        await self.redis.delete(*keys)
        return True

    async def health_check(self) -> bool:
        """
        Check the availability of Redis
        Returns:
            bool: True if Redis is available
        """
        try:
            return await self.redis.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False 