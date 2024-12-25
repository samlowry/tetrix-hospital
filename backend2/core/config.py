from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load environment variables from local .env
load_dotenv()

class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str = "tetrix"
    POSTGRES_PASSWORD: str = "tetrixpass"
    POSTGRES_DB: str = "tetrix"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    
    # Workers and Connections
    WORKER_COUNT: int = (os.cpu_count() or 1) * 2 + 1
    CONNECTIONS_PER_WORKER: int = 5
    MAX_OVERFLOW_PER_WORKER: int = 10
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    BACKEND_URL: str
    FRONTEND_URL: str
    
    # Application
    FLASK_ENV: str = "development"
    JWT_SECRET_KEY: str
    
    # Hardcoded for security - obscure webhook path with random suffix
    WEBHOOK_PATH: str = '/telegram-webhook9eu3f3843ry9834843'
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    @property
    def WEBHOOK_URL(self) -> str:
        return f"{self.BACKEND_URL}{self.WEBHOOK_PATH}"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in environment without validation

@lru_cache()
def get_settings():
    return Settings() 