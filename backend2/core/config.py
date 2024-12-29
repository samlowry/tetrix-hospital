# Import required libraries for configuration management
from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load environment variables from local .env file into the application
load_dotenv()

class Settings(BaseSettings):
    """Main configuration settings class for the application"""
    
    # Database connection settings
    POSTGRES_USER: str = "tetrix"          # PostgreSQL username
    POSTGRES_PASSWORD: str = "tetrixpass"   # PostgreSQL password
    POSTGRES_DB: str = "tetrix"            # PostgreSQL database name
    POSTGRES_HOST: str = "postgres"         # PostgreSQL host address
    POSTGRES_PORT: int = 5432              # PostgreSQL port number
    
    # Application worker and connection pool settings
    WORKER_COUNT: int = (os.cpu_count() or 1) * 2 + 1  # Number of workers based on CPU cores
    CONNECTIONS_PER_WORKER: int = 5        # Database connections per worker
    MAX_OVERFLOW_PER_WORKER: int = 10      # Maximum additional connections allowed per worker
    
    # Redis cache settings
    REDIS_HOST: str = "redis"              # Redis host address
    REDIS_PORT: int = 6379                 # Redis port number
    
    # Telegram integration settings
    TELEGRAM_BOT_TOKEN: str                # Authentication token for Telegram bot
    BACKEND_URL: str                       # URL for the backend service
    FRONTEND_URL: str                      # URL for the frontend service
    
    # Application security settings
    FLASK_ENV: str = "development"         # Flask environment mode
    JWT_SECRET_KEY: str                    # Secret key for JWT token generation
    
    # Webhook configuration
    WEBHOOK_PATH: str = '/telegram-webhook9eu3f3843ry9834843'  # Secure webhook endpoint path
    
    @property
    def DATABASE_URL(self) -> str:
        """Constructs and returns the complete PostgreSQL database URL"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def REDIS_URL(self) -> str:
        """Constructs and returns the complete Redis URL"""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    @property
    def WEBHOOK_URL(self) -> str:
        """Constructs and returns the complete webhook URL"""
        return f"{self.BACKEND_URL}{self.WEBHOOK_PATH}"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in environment without validation

@lru_cache()
def get_settings():
    return Settings() 