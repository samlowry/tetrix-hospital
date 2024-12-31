from enum import Enum
from aiocache import caches, Cache
from aiocache.backends.redis import RedisCache
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import json

logger = logging.getLogger(__name__)

class CacheTTL(Enum):
    """TTL values for different types of cached data"""
    NONE = None  # Permanent storage (user states, bot state)
    METRICS = 90  # DexScreener and holders data (90 seconds)
    DEFAULT = 432000  # 5 days default from redis_service

class CacheKeys:
    """Cache key patterns used throughout the application"""
    USER_STATUS = "user:{telegram_id}:status"
    USER_CONTEXT = "user:{telegram_id}:context"
    USER_SESSION = "user_sessions:{telegram_id}"
    USER_LANGUAGE = "user:{telegram_id}:language"
    
    # Bot related
    BOT = "bot"                            # Base key for bot-related data
    BOT_STATE = "bot:state"                # Stores the current state of the bot
    BOT_DATA = "bot:data"                  # General bot data storage
    BOT_WEBHOOK_URL = "bot:webhook_url"    # URL for bot webhook
    BOT_USER_DATA = "bot:user_data"        # User-specific data storage
    BOT_CHAT_DATA = "bot:chat_data"        # Chat-specific data storage
    BOT_CALLBACK_DATA = "bot:callback_data" # Callback query data
    BOT_CONVERSATIONS = "bot:conversations" # Conversation state tracking
    BOT_INITIALIZED = "bot:initialized"     # Bot initialization flag
    
    # Metrics related
    DEX_SCREENER = "tetrix:dexscreener"
    HOLDERS = "tetrix:holders"
    METRICS = "tetrix:metrics"

def setup_cache() -> Cache:
    """Configure and return aiocache instance with same settings as current Redis"""
    config = {
        'default': {
            'cache': "aiocache.RedisCache",
            'endpoint': "redis",  # from current config
            'port': 6379,
            'timeout': 10,
            'serializer': {
                'class': "aiocache.serializers.StringSerializer"
            },
            'plugins': [
                {'class': "aiocache.plugins.HitMissRatioPlugin"},
                {'class': "aiocache.plugins.TimingPlugin"}
            ]
        }
    }
    
    try:
        caches.set_config(config)
        cache = caches.get('default')
        logger.info("Cache configuration successful")
        return cache
    except Exception as e:
        logger.error(f"Failed to configure cache: {e}")
        raise

def cache_result(
    key_pattern: str = None,
    ttl: Optional[int] = CacheTTL.DEFAULT.value,
    namespace: Optional[str] = None
):
    """Base decorator for all cache operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get instance (self) from args
            instance = args[0] if args else None
            
            # Filter out session objects from key generation
            clean_args = [arg for arg in args[1:] if not isinstance(arg, AsyncSession)]
            clean_kwargs = {k: v for k, v in kwargs.items() if not isinstance(v, AsyncSession)}
            
            # Key generation logic
            if key_pattern:
                try:
                    # Try to format with cleaned kwargs first
                    format_args = clean_kwargs.copy()
                    # Add positional args to format_args
                    if clean_args:
                        # If first arg is telegram_id, use it
                        if len(clean_args) > 0 and 'telegram_id' in key_pattern:
                            format_args['telegram_id'] = clean_args[0]
                    key = key_pattern.format(**format_args)
                except KeyError as e:
                    logger.error(f"Failed to format key pattern {key_pattern} with args {format_args}: {e}")
                    # Use pattern as is if formatting fails
                    key = key_pattern
            else:
                # Default key from function name and cleaned args
                key = f"{func.__name__}:{':'.join(str(arg) for arg in clean_args)}"
            
            if instance and hasattr(instance, 'cache') and instance.cache:
                cache = instance.cache
                logger.debug(f"Cache key: {key}")
                
                # Try to get from cache first
                cached = await cache.get(key)
                if cached is not None:
                    # Only try to deserialize if we got a string that looks like JSON
                    if isinstance(cached, str) and (cached.startswith('{') or cached.startswith('[')):
                        try:
                            return json.loads(cached)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode JSON from cache for key {key}, raw value: {cached[:100]}")
                            # Return original value if can't deserialize
                            return cached
                    return cached
                
                # If not in cache, call function
                result = await func(*args, **kwargs)
                
                # Cache the result
                if result is not None:
                    try:
                        # If result is dict or list, serialize to JSON before caching
                        if isinstance(result, (dict, list)):
                            result_to_cache = json.dumps(result)
                        else:
                            result_to_cache = result
                        await cache.set(key, result_to_cache, ttl=ttl)
                    except Exception as e:
                        logger.error(f"Failed to cache result for key {key}: {e}")
                
                return result
            else:
                # No cache available, just call function
                return await func(*args, **kwargs)
                
        return wrapper
    return decorator

def cache_metrics(ttl: int = CacheTTL.METRICS.value, key_pattern: str = None):
    """Decorator for caching metrics data"""
    return cache_result(key_pattern=key_pattern, ttl=ttl)

def cache_permanent(key_pattern: str = None):
    """Decorator for permanent cache storage (no TTL)"""
    return cache_result(key_pattern=key_pattern, ttl=None) 