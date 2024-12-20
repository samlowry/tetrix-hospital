import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables first
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try current directory
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(env_path)

# Constants
# Hardcoded for security - obscure webhook path with random suffix
WEBHOOK_PATH = '/telegram-webhook9eu3f3843ry9834843'

# Redis
# Standard Redis port - no need to make configurable as it's industry standard
REDIS_PORT = 6379
# Docker internal hostname and local dev hostname - controlled by docker-compose in prod
REDIS_HOST_PROD = 'redis'
REDIS_HOST_DEV = 'localhost'

# Redis connection settings
REDIS_HOST = REDIS_HOST_DEV if os.getenv('FLASK_ENV') == 'development' else REDIS_HOST_PROD
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# Construct webhook URL
backend_url = os.getenv('BACKEND_URL')
if not backend_url:
    raise ValueError("BACKEND_URL environment variable is required")
WEBHOOK_URL = f"{backend_url}{WEBHOOK_PATH}"
logger.info(f"Using webhook URL: {WEBHOOK_URL}")