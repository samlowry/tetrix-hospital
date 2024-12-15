from functools import wraps
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging

logger = logging.getLogger('tetrix')

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def log_api_call(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            logger.info(f"API call: {f.__name__} - {request.remote_addr}")
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}")
            raise
    return decorated 