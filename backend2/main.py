from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from .services.scheduler_service import SchedulerService
import asyncio

from routers.telegram import router as telegram_router
from routers.ton_connect import router as ton_connect_router
from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(title="TETRIX Bot API")
scheduler: SchedulerService = None

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Тестовый роут
@app.get("/test")
async def test():
    return {"message": "Test route works!"}

# Подключаем роутеры
app.include_router(telegram_router)
app.include_router(ton_connect_router)

@app.on_event("startup")
async def startup_event():
    """Действия при запуске приложения"""
    global scheduler
    redis = await get_redis()
    session = await get_session()
    
    # Initialize scheduler
    scheduler = SchedulerService(redis, session)
    
    # Fetch all metrics first time and retry if failed
    for _ in range(3):  # Try 3 times
        try:
            await scheduler.fetch_all_metrics()
            break
        except Exception as e:
            logger.error(f"Error fetching initial metrics: {e}")
            await asyncio.sleep(1)  # Wait 1 second before retry
    
    # Start scheduler
    scheduler.start()

    # Устанавливаем вебхук для Telegram
    if settings.BACKEND_URL:
        from routers.telegram import setup_webhook
        await setup_webhook()
    else:
        logger.warning("BACKEND_URL not set, skipping webhook setup")

@app.on_event("shutdown")
async def shutdown_event():
    if scheduler:
        scheduler.stop()