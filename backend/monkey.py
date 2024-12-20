from gevent import monkey
import warnings

# Ignore warnings about asyncio
warnings.filterwarnings('ignore', category=RuntimeWarning, message='coroutine .* was never awaited')

# Patch before any other imports
monkey.patch_all(
    socket=True,
    dns=True,
    time=True,
    select=True,
    thread=True,
    os=True,
    ssl=True,
    httplib=False,
    subprocess=True,
    sys=False,
    aggressive=True,
    Event=False,
    builtins=True,
    signal=True
) 