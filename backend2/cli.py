import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import get_session_local
from services.user_service import UserService

logging.basicConfig(level=logging.INFO)

async def test_create_user():
    """Тест функции create_user"""
    session: AsyncSession = await get_session_local()
    try:
        user_service = UserService(session)
        # Тестовый адрес, которого нет в списке
        wallet_address = "0:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        telegram_id = 987654321
        
        user = await user_service.create_user(telegram_id, wallet_address)
        print(f"Created user: {user.wallet_address}")
        print(f"Is early backer: {user.is_early_backer}")
        print(f"Is fully registered: {user.is_fully_registered}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(test_create_user()) 