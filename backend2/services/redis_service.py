from redis.asyncio import Redis, ConnectionPool
from datetime import timedelta, datetime
import json
import logging
from typing import Optional, Dict
from enum import Enum

logger = logging.getLogger(__name__)

class UserStatus(Enum):
    WAITING_WALLET = "waiting_wallet"  # Ожидание подключения кошелька
    WAITING_INVITE = "waiting_invite"  # Ожидание ввода инвайт-кода
    REGISTERED = "registered"          # Полностью зарегистрирован

# Redis keys
REDIS_KEYS = {
    'bot': 'bot',
    'bot_state': 'bot:state',
    'bot_data': 'bot:data',
    'webhook_url': 'bot:webhook_url',
    'user_data': 'bot:user_data',
    'chat_data': 'bot:chat_data',
    'callback_data': 'bot:callback_data',
    'conversations': 'bot:conversations',
    'user_sessions': 'user_sessions',
    'initialized': 'bot:initialized',
    'user_status': 'user:{}:status'  # Ключ для хранения статуса пользователя
}

class RedisService:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.default_ttl = timedelta(days=5)

    @classmethod
    def create(cls, host: str = 'redis', port: int = 6379):
        """Создание экземпляра сервиса с настроенным Redis клиентом"""
        pool = ConnectionPool(
            host=host,
            port=port,
            db=0,
            decode_responses=True,  # Автоматически декодируем ответы в UTF-8
            socket_timeout=10,
            socket_connect_timeout=10,
            socket_keepalive=True,
            health_check_interval=15,
            max_connections=100,
            retry_on_timeout=True
        )
        redis = Redis(connection_pool=pool)
        return cls(redis)

    # Методы для работы со статусом пользователя
    async def get_user_status(self, telegram_id: int) -> Optional[UserStatus]:
        """Get user status"""
        value = await self.get_user_status_value(telegram_id)
        if value is None:
            return None
        return UserStatus(value)

    async def set_user_status(self, telegram_id: int, status: dict) -> bool:
        """Установка статуса пользователя"""
        key = REDIS_KEYS['user_status'].format(telegram_id)
        await self.redis.set(key, json.dumps(status), ex=self.default_ttl)
        return True

    async def update_user_status(self, telegram_id: int, **kwargs) -> bool:
        """Обновление отдельных полей статуса пользователя"""
        current_status = await self.get_user_status(telegram_id) or {}
        current_status.update(kwargs)
        return await self.set_user_status(telegram_id, current_status)

    async def set_status_waiting_wallet(self, telegram_id: int) -> bool:
        """Установка статуса ожидания подключения кошелька"""
        return await self.set_user_status(telegram_id, {
            'status': UserStatus.WAITING_WALLET.value,
            'updated_at': datetime.utcnow().isoformat()
        })

    async def set_status_waiting_invite(self, telegram_id: int) -> bool:
        """Установка статуса ожидания инвайт-кода"""
        return await self.set_user_status(telegram_id, {
            'status': UserStatus.WAITING_INVITE.value,
            'updated_at': datetime.utcnow().isoformat()
        })

    async def set_status_registered(self, telegram_id: int) -> bool:
        """Установка статуса полной регистрации"""
        return await self.set_user_status(telegram_id, {
            'status': UserStatus.REGISTERED.value,
            'updated_at': datetime.utcnow().isoformat()
        })

    async def get_user_status_value(self, telegram_id: int) -> Optional[str]:
        """Get user status value"""
        key = f"user:{telegram_id}:status"
        value = await self.redis.get(key)
        return value.decode('utf-8') if value else None

    # Методы для работы с состоянием пользователя
    async def get_user_state(self, telegram_id: int) -> Optional[Dict]:
        """Get current user state"""
        key = f"user:{telegram_id}:state"
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def set_user_state(self, telegram_id: int, state: str) -> bool:
        """Установка состояния пользователя"""
        key = f"user:{telegram_id}:state"
        await self.redis.set(key, state, ex=self.default_ttl)
        return True

    # Методы для работы с контекстом пользователя
    async def get_context(self, telegram_id: int) -> dict:
        """Получение контекста диалога"""
        key = f"user:{telegram_id}:context"
        context = await self.redis.get(key)
        if context:
            try:
                return json.loads(context)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode context for user {telegram_id}")
        return {}

    async def update_context(self, telegram_id: int, context: dict) -> bool:
        """Обновление контекста диалога"""
        key = f"user:{telegram_id}:context"
        await self.redis.set(key, json.dumps(context), ex=self.default_ttl)
        return True

    # Методы для работы с состоянием бота
    async def get_bot_state(self) -> Optional[Dict]:
        """Get bot state"""
        value = await self.redis.get('bot:state')
        return json.loads(value) if value else None

    async def set_bot_state(self, state: str) -> bool:
        """Установка состояния бота"""
        await self.redis.set(REDIS_KEYS['bot_state'], state)
        return True

    async def is_bot_initialized(self) -> bool:
        """Check if bot is initialized"""
        value = await self.redis.get('bot:initialized')
        return value == b'true'

    async def set_bot_initialized(self) -> bool:
        """Отметка об инициализации бота"""
        await self.redis.set(REDIS_KEYS['initialized'], 'true')
        return True

    # Методы для работы с сессиями
    async def get_user_session(self, telegram_id: int) -> Optional[Dict]:
        """Get user session"""
        key = f"user:{telegram_id}:session"
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def set_user_session(self, user_id: int, session_data: dict) -> bool:
        """Установка сессии пользователя"""
        await self.redis.set(
            f"{REDIS_KEYS['user_sessions']}:{user_id}",
            json.dumps(session_data),
            ex=self.default_ttl
        )
        return True

    async def clear_user_data(self, telegram_id: int) -> bool:
        """Очистка всех данных пользователя"""
        keys = [
            f"user:{telegram_id}:state",
            f"user:{telegram_id}:context",
            f"{REDIS_KEYS['user_sessions']}:{telegram_id}",
            REDIS_KEYS['user_status'].format(telegram_id)
        ]
        await self.redis.delete(*keys)
        return True

    async def check_redis_health(self) -> bool:
        """Check Redis availability"""
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False 