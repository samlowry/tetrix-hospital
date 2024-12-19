import os

# Constants
# Hardcoded for security - obscure webhook path with random suffix
WEBHOOK_PATH = '/telegram-webhook9eu3f3843ry9834843'

# Construct webhook URL once
WEBHOOK_URL = f"{os.getenv('BACKEND_URL')}{WEBHOOK_PATH}" 

# Redis
# Standard Redis port - no need to make configurable as it's industry standard
REDIS_PORT = 6379
# Docker internal hostname and local dev hostname - controlled by docker-compose in prod
REDIS_HOST_PROD = 'redis'
REDIS_HOST_DEV = 'localhost'