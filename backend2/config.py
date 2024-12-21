import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Try default locations

# FastAPI settings
FASTAPI_HOST = os.getenv('FASTAPI_HOST', '0.0.0.0')
FASTAPI_PORT = int(os.getenv('FASTAPI_PORT', 5000))
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# Database settings
POSTGRES_USER = os.getenv('POSTGRES_USER', 'tetrix')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'tetrixpass')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'tetrix')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Redis settings
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_PATH = '/telegram-webhook9eu3f3843ry9834843'  # Keep the same as in old app
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Security settings
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default-secret-key')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DAYS = 30

# TON settings
TETRIX_CONTRACT_ADDRESS = os.getenv('TETRIX_CONTRACT_ADDRESS')

# Constants
ALLOWED_DOMAINS = {'localhost', 'app.tetrix.xyz'}  # Add your domains here
VALID_AUTH_TIME = 300  # 5 minutes for TON proof 