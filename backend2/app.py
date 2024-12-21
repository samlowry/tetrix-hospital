from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

# Роутеры
from routers import telegram, ton_connect, api
from models.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()  # Создаем таблицы если их нет
    await telegram.setup_webhook()
    yield
    # Shutdown
    pass

# Создаем FastAPI приложение
app = FastAPI(
    title="Tetrix Hospital Bot",
    lifespan=lifespan
)

# Настраиваем CORS для веб-приложения
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для разработки разрешаем все источники
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Подключаем роутеры
app.include_router(telegram.router)  # Telegram бот
app.include_router(ton_connect.router)  # TON Connect авторизация
app.include_router(api.router)  # API для партнерского приложения

# Тестовый эндпоинт
@app.get("/")
async def root():
    return {"status": "ok", "message": "Tetrix Hospital Bot is running"}

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=True
    ) 