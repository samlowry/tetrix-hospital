import multiprocessing
import tempfile

# Use single worker for better stability with gevent
workers = 1

# Use more threads for I/O operations
threads = multiprocessing.cpu_count() * 2

# Use gevent worker class for async support
worker_class = 'gevent'

# Prevent gunicorn from doing its own monkey patching
enable_monkey_patching = False

# Increase worker connections for better concurrency
worker_connections = 1000

# Optimize worker lifecycle
max_requests = 1000
max_requests_jitter = 50

# Adjust timeouts
timeout = 120
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'debug'
capture_output = True
enable_stdio_inheritance = True

# Log formatting
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

# Bind address
bind = '0.0.0.0:5000'

# Gevent specific settings
worker_tmp_dir = tempfile.gettempdir()
backlog = 2048

# Performance optimizations
sendfile = True
tcp_nopush = True
tcp_nodelay = True

# Keep-alive settings
keepalive_timeout = 65
timeout = 120

# Allow forwarded IPs
forwarded_allow_ips = '*'

# Prevent worker timeout
graceful_timeout = 120

# Preload app for better performance
preload_app = False  # Important: Keep this False for gevent

# Server hooks
def on_starting(server):
    """Run before the server starts accepting requests"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Running Gunicorn pre-start initialization...")

# Worker class specific settings
worker_class_args = {
    'worker_connections': 1000,
    'keepalive': 5,
}