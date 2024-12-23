from functools import wraps
from flask import request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os
import hashlib
from config import REDIS_URL  # Import centralized Redis URL

logger = logging.getLogger('tetrix')

def get_device_identifier():
    """Generate a unique device identifier from IP and User-Agent"""
    ip = get_remote_address()
    user_agent = request.headers.get('User-Agent', '')
    device_string = f"{ip}:{user_agent}"
    # Hash the string to keep the key length manageable
    return hashlib.md5(device_string.encode()).hexdigest()

limiter = Limiter(
    key_func=get_device_identifier,
    default_limits=["1000 per hour", "10000 per day"],
    storage_uri=REDIS_URL,  # Use centralized Redis URL
    strategy="fixed-window"
)

def log_api_call(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.info(f"API call: {request.method} {request.path}")
        return f(*args, **kwargs)
    return decorated_function

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != 'kusaikuracsubalkfheaksjfhakjfhka':
            return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function