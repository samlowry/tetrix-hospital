import asyncio
import logging
import uvicorn
import multiprocessing
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import get_session_local
from services.user_service import UserService
from migrations.migrate import run_migrations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def run_server():
    """Запуск сервера с workers для тестирования"""
    workers = (multiprocessing.cpu_count() * 2) + 1
    logger.info("Running database migrations...")
    try:
        run_migrations()
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise

    logger.info(f"Starting server with {workers} workers...")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        workers=workers,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        run_server()
    else:
        asyncio.run(test_create_user()) 