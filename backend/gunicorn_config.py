import multiprocessing
import os

# Number of worker processes
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))

# Use gevent worker class for async support
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'gevent')

# Maximum requests before worker restart
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', 1000))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', 50))

# Timeouts
timeout = int(os.getenv('GUNICORN_TIMEOUT', 120))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', 5))

# Logging
accesslog = os.getenv('GUNICORN_ACCESS_LOG', 'access.log')
errorlog = os.getenv('GUNICORN_ERROR_LOG', 'error.log')
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')

# Bind address
bind = f"{os.getenv('APP_HOST', '0.0.0.0')}:{os.getenv('APP_PORT', '5000')}"

# Preload app for faster worker startup
preload_app = os.getenv('GUNICORN_PRELOAD', 'true').lower() == 'true' 