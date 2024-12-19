import os

# Constants
# Hardcoded for security - obscure webhook path with random suffix
WEBHOOK_PATH = '/telegram-webhook9eu3f3843ry9834843'

# Redis
# Standard Redis port - no need to make configurable as it's industry standard
REDIS_PORT = 6379
# Docker internal hostname and local dev hostname - controlled by docker-compose in prod
REDIS_HOST_PROD = 'redis'
REDIS_HOST_DEV = 'localhost'

# URL will be constructed after env is loaded
WEBHOOK_URL = None

def init_webhook_url():
    global WEBHOOK_URL
    backend_url = os.getenv('BACKEND_URL')
    print(f"Backend URL from env: {backend_url}")
    WEBHOOK_URL = f"{backend_url}{WEBHOOK_PATH}"
    print(f"Constructed webhook URL: {WEBHOOK_URL}")