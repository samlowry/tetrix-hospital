from functools import wraps
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os
import hashlib

logger = logging.getLogger('tetrix')

def get_device_identifier():
    """Generate a unique device identifier from IP and User-Agent"""
    ip = get_remote_address()
    user_agent = request.headers.get('User-Agent', '')
    device_string = f"{ip}:{user_agent}"
    # Hash the string to keep the key length manageable
    return hashlib.md5(device_string.encode()).hexdigest()

redis_host = os.getenv('REDIS_HOST', 'redis')
redis_port = int(os.getenv('REDIS_PORT', 6379))
redis_db = int(os.getenv('REDIS_DB', 0))
redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=redis_url,
    default_limits=["200 per day", "50 per hour"]
)

def log_api_call(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            logger.info(f"API call: {f.__name__} - Device: {get_device_identifier()}")
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}")
            raise
    return decorated 