import os

# Constants
WEBHOOK_PATH = '/telegram-webhook9eu3f3843ry9834843'
TON_API_ENDPOINT = 'https://toncenter.com/api/v2/jsonRPC'

# Construct webhook URL once
WEBHOOK_URL = f"{os.getenv('BACKEND_URL')}{WEBHOOK_PATH}" 