from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from routers.telegram import router as telegram_router
from routers.ton_connect import router as ton_connect_router
from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(title="TETRIX Bot API")

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
    # Устанавливаем вебхук для Telegram
    if settings.BACKEND_URL:
        from routers.telegram import setup_webhook
        await setup_webhook()
    else:
        logger.warning("BACKEND_URL not set, skipping webhook setup") 