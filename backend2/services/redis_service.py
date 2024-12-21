import json
from typing import Optional, Dict, Any
from redis.asyncio import Redis
from datetime import timedelta

class RedisService:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.state_prefix = "tg:state:"
        self.context_prefix = "tg:context:"
        self.default_ttl = timedelta(days=5)  # Состояние хранится 5 дней

    async def get_user_state(self, telegram_id: int) -> Optional[str]:
        """Получить текущее состояние пользователя"""
        key = f"{self.state_prefix}{telegram_id}"
        state = await self.redis.get(key)
        return state.decode() if state else None

    async def set_user_state(self, telegram_id: int, state: str) -> bool:
        """Установить состояние пользователя"""
        key = f"{self.state_prefix}{telegram_id}"
        return await self.redis.set(key, state, ex=self.default_ttl)

    async def get_context(self, telegram_id: int) -> Dict:
        """Получить контекст диалога"""
        key = f"{self.context_prefix}{telegram_id}"
        data = await self.redis.get(key)
        return json.loads(data) if data else {}

    async def update_context(self, telegram_id: int, update_data: Dict[str, Any]) -> bool:
        """Обновить контекст диалога"""
        key = f"{self.context_prefix}{telegram_id}"
        current_data = await self.get_context(telegram_id)
        current_data.update(update_data)
        return await self.redis.set(
            key,
            json.dumps(current_data),
            ex=self.default_ttl
        )

    async def clear_user_data(self, telegram_id: int) -> bool:
        """Очистить все данные пользователя"""
        state_key = f"{self.state_prefix}{telegram_id}"
        context_key = f"{self.context_prefix}{telegram_id}"
        
        async with self.redis.pipeline() as pipe:
            await pipe.delete(state_key)
            await pipe.delete(context_key)
            results = await pipe.execute()
        
        return all(results) 