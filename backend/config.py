import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables first
env_path = Path(__file__).resolve().parent.parent / '.env'
print(f"Looking for .env at: {env_path.absolute()}")
if not env_path.exists():
    # Try current directory
    env_path = Path('.env')
    print(f"Not found, trying current directory: {env_path.absolute()}")
if env_path.exists():
    print(f"Found .env file at: {env_path.absolute()}")
    load_dotenv(env_path)
    print(f"Loaded TELEGRAM_BOT_TOKEN: {os.getenv('TELEGRAM_BOT_TOKEN')}")
else:
    print("No .env file found!")

# Constants
# Hardcoded for security - obscure webhook path with random suffix
WEBHOOK_PATH = '/telegram-webhook9eu3f3843ry9834843'

# Redis
# Standard Redis port - no need to make configurable as it's industry standard
REDIS_PORT = 6379
# Docker internal hostname and local dev hostname - controlled by docker-compose in prod
REDIS_HOST_PROD = 'redis'
REDIS_HOST_DEV = 'localhost'

# Construct webhook URL
backend_url = os.getenv('BACKEND_URL')
if not backend_url:
    raise ValueError("BACKEND_URL environment variable is required")
WEBHOOK_URL = f"{backend_url}{WEBHOOK_PATH}"
print(f"Constructed webhook URL: {WEBHOOK_URL}")