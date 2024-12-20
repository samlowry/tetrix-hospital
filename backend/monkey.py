from gevent import monkey
import warnings

# Ignore warnings about asyncio
warnings.filterwarnings('ignore', category=RuntimeWarning, message='coroutine .* was never awaited')

# Patch only what we need
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