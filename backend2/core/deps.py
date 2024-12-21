from redis.asyncio import Redis
from typing import AsyncGenerator
from .config import get_settings

settings = get_settings()

async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    Получение Redis клиента
    """
    client = Redis(
        host="localhost",
        port=6379,
        db=0,
        decode_responses=True
    )
    try:
        yield client
    finally:
        await client.close() 