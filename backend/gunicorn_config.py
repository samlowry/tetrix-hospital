import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'gevent'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'tetrix-backend'

# SSL
keyfile = None
certfile = None

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Prevent double monkey patching
preload_app = True

def post_fork(server, worker):
    # Reset all connections after fork
    from gevent import monkey
    monkey.patch_all(
        socket=True,
        dns=True,
        time=True,
        select=True,
        thread=True,
        os=True,
        ssl=True,
        httplib=False,
        subprocess=False,
        sys=False,
        aggressive=False,
        Event=False,
        builtins=False,
        signal=False
    )