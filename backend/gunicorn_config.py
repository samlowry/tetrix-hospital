import multiprocessing

# Use fewer workers for bot application
workers = 2  # Reduced from cpu_count() * 2 + 1

# Use gevent worker class
worker_class = 'gevent'

# Worker connections for gevent
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

# Don't preload app with gevent
preload_app = False

# Allow forwarded IPs
forwarded_allow_ips = '*'

# Prevent worker timeout
graceful_timeout = 120

# Thread configuration
threads = 4