import multiprocessing

# Number of worker processes
workers = multiprocessing.cpu_count() * 2 + 1

# Use gevent worker class for async support
worker_class = 'gevent'
worker_connections = 1000

# Maximum requests before worker restart
max_requests = 1000
max_requests_jitter = 50

# Timeouts
timeout = 120
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Bind address
bind = '0.0.0.0:5000'

# Preload app for faster worker startup
preload_app = True

# Gevent specific settings
worker_tmp_dir = '/dev/shm'
forwarded_allow_ips = '*'

# Prevent worker timeout
graceful_timeout = 120