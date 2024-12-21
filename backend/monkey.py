from gevent import monkey
import warnings

# Ignore warnings about asyncio
warnings.filterwarnings('ignore', category=RuntimeWarning, message='coroutine .* was never awaited')

# Check if already patched to prevent double patching
if not monkey.is_module_patched('socket'):
    # Patch all necessary modules
    monkey.patch_all(
        socket=True,
        dns=True,
        time=True,
        select=True,
        thread=False,
        os=True,
        ssl=True,
        httplib=False,
        subprocess=True,
        sys=False,
        aggressive=False,
        Event=False,
        builtins=True,
        signal=True
    ) 