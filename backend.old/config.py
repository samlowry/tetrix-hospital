import os
import logging
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from local .env
load_dotenv()

# Constants
# Hardcoded for security - obscure webhook path with random suffix
WEBHOOK_PATH = '/telegram-webhook9eu3f3843ry9834843'

# Redis
# Standard Redis port - no need to make configurable as it's industry standard
REDIS_PORT = 6379
# Always use redis as host for both dev and prod
REDIS_HOST = 'redis'
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# Database
POSTGRES_USER = os.getenv('POSTGRES_USER', 'tetrix')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'tetrixpass')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'tetrix')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

# Construct webhook URL
BACKEND_URL = os.getenv('BACKEND_URL')
if not BACKEND_URL:
    raise ValueError("BACKEND_URL environment variable is required")
WEBHOOK_URL = f"{BACKEND_URL}{WEBHOOK_PATH}"
logger.info(f"Using webhook URL: {WEBHOOK_URL}")