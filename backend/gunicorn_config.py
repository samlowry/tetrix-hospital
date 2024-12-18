import multiprocessing

# Number of worker processes
workers = multiprocessing.cpu_count() * 2 + 1

# Use gevent worker class for async support
worker_class = 'gevent'

# Maximum requests before worker restart
max_requests = 1000
max_requests_jitter = 50

# Timeouts
timeout = 120
keepalive = 5

# Logging
accesslog = 'access.log'
errorlog = 'error.log'
loglevel = 'info'

# Bind address
bind = '0.0.0.0:5000'

# Preload app for faster worker startup
preload_app = True 