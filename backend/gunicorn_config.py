import multiprocessing
import tempfile

# Optimize number of workers based on CPU cores
workers = multiprocessing.cpu_count() * 2 + 1

# Use gevent worker class for async support
worker_class = 'gevent'

# Increase worker connections for better concurrency
worker_connections = 2000

# Optimize worker lifecycle
max_requests = 2000
max_requests_jitter = 100

# Adjust timeouts
timeout = 300
keepalive = 10

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Bind address
bind = '0.0.0.0:5000'

# Enable threading
threads = multiprocessing.cpu_count() * 2

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