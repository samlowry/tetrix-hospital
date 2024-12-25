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

# Load settings
settings = Settings()

# Routers
from routers import telegram, ton_connect, api
from models.database import init_db, engine

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all logs
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Set log levels for specific loggers
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

# Get our logger
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Initialize Redis
    redis = RedisService.create(settings.REDIS_HOST, settings.REDIS_PORT)
    app.state.redis = redis.redis

    # Initialize database
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    app.state.async_session = async_session

    # Create tables and run migrations
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Run SQL migrations
    logger.info("Running SQL migrations...")
    try:
        run_migrations()
        logger.info("SQL migrations completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise

    # Initialize scheduler
    scheduler = SchedulerService(redis.redis, async_session)
    app.state.scheduler = scheduler
    await scheduler.start()

    yield

    # Cleanup
    await scheduler.stop()
    await engine.dispose()
    await app.state.redis.close()

# Create FastAPI application
app = FastAPI(
    title="Tetrix Hospital Bot",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "tryItOutEnabled": True,
        "displayRequestDuration": True
    }
)

# Configure CORS for web application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Connect routers
app.include_router(telegram.router)  # Telegram bot
app.include_router(ton_connect.router)  # TON Connect authorization
app.include_router(api.router)  # API for partner application

# Test endpoint
@app.get("/")
async def root():
    return {"status": "ok", "message": "Tetrix Hospital Bot is running"}

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="debug"  # Set Uvicorn log level to debug
    ) 