# Import required libraries for async operations, logging, server management and database
import asyncio
import logging
import uvicorn
import multiprocessing
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import get_session_local
from services.user_service import UserService
from migrations.migrate import run_migrations

# Configure basic logging settings
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_create_user():
    """Test function to create a new user in the system"""
    # Get database session
    session: AsyncSession = await get_session_local()
    try:
        # Initialize user service with database session
        user_service = UserService(session)
        # Test wallet address that doesn't exist in the list
        wallet_address = "0:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        # Sample Telegram user ID
        telegram_id = 987654321
        
        # Create new user and print their details
        user = await user_service.create_user(telegram_id, wallet_address)
        print(f"Created user: {user.wallet_address}")
        print(f"Is early backer: {user.is_early_backer}")
        print(f"Is fully registered: {user.is_fully_registered}")
    finally:
        # Ensure database session is closed
        await session.close()

def run_server():
    """Function to start the server with optimal number of workers"""
    # Calculate optimal number of workers based on CPU cores
    workers = (multiprocessing.cpu_count() * 2) + 1
    logger.info("Running database migrations...")
    try:
        # Execute database migrations
        run_migrations()
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise

    # Start the server with configured settings
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
    # Script entry point - either runs the server or tests user creation
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        run_server()
    else:
        asyncio.run(test_create_user())