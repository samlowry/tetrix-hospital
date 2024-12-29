# Redis and typing imports for async functionality
from redis.asyncio import Redis
from typing import AsyncGenerator
from .config import get_settings

# Global settings instance from configuration
settings = get_settings()

async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    Creates and manages a Redis client connection
    
    Returns:
        AsyncGenerator[Redis, None]: A Redis client instance that automatically 
        handles connection lifecycle
    """
    # Initialize Redis client with configuration from settings
    client = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
        decode_responses=True  # Automatically decode Redis responses to strings
    )
    try:
        yield client
    finally:
        # Ensure proper cleanup of Redis connection
        await client.close()