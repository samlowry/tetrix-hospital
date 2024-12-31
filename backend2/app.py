# Import required libraries and modules
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager
import logging
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from services.redis_service import RedisService
from services.scheduler_service import SchedulerService
from services.tetrix_service import TetrixService
from core.config import Settings
from models.database import init_db, engine, Base
from migrations.migrate import run_migrations
from core.cache import setup_cache

# Initialize application settings from environment variables
settings = Settings()

# Import route handlers for different endpoints
from routers import telegram, ton_connect, api
from models.database import init_db, engine

# Set up application logging configuration
logging.basicConfig(
    level=logging.DEBUG,  # Debug level logging for development
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Configure logging levels for specific components
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

# Create logger instance for this module
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application lifecycle, including initialization and cleanup of services
    Args:
        app: FastAPI application instance
    """
    # Initialize Cache
    app.state.cache = setup_cache()
    logger.info("Cache initialized")

    # Initialize Redis service with async client
    # We use both aiocache (app.state.cache) and direct async Redis client (app.state.redis)
    # Direct Redis client is used as fallback when cache is unavailable
    redis = RedisService.create(settings.REDIS_HOST, settings.REDIS_PORT)
    app.state.redis = redis.redis  # Async Redis client instance
    app.state.redis_service = redis  # Store service instance for fallback operations
    app.state.redis_service.cache = app.state.cache  # Connect cache to service for primary operations

    # Set up database connection and session manager
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    app.state.async_session = async_session

    # Initialize database tables
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Set up and start the task scheduler with new cache
    scheduler = SchedulerService(app.state.cache, async_session)
    app.state.scheduler = scheduler
    await scheduler.start()

    yield

    # Cleanup resources on shutdown
    await scheduler.stop()
    await engine.dispose()
    await app.state.redis.close()
    await app.state.cache.close()
    logger.info("All resources cleaned up")

# Initialize FastAPI application with configuration
app = FastAPI(
    title="Tetrix Hospital Bot",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "tryItOutEnabled": True,
        "displayRequestDuration": True
    }
)

# Configure CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register route handlers
app.include_router(telegram.router)  # Handle Telegram bot interactions
app.include_router(ton_connect.router)  # Handle TON wallet authentication
app.include_router(api.router)  # Handle partner application API requests

# Health check endpoint
@app.get("/")
async def root():
    """
    Simple health check endpoint to verify service status
    Returns:
        dict: Status message indicating service is running
    """
    return {"status": "ok", "message": "Tetrix Hospital Bot is running"}

if __name__ == "__main__":
    # Run the application server (development mode)
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="debug"  # Enable debug logging for development
    )