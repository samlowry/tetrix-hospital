from gevent import monkey
import warnings

# Ignore warnings about asyncio
warnings.filterwarnings('ignore', category=RuntimeWarning, message='coroutine .* was never awaited')

# Check if already patched to prevent double patching
if not monkey.is_module_patched('socket'):
    # Patch only what we need, keeping threading intact for APScheduler
    monkey.patch_all(
        socket=True,
        dns=True,
        time=True,
        select=True,
        thread=False,  # Don't patch threading
        os=True,
        ssl=True,
        httplib=False,
        subprocess=True,
        sys=False,
        aggressive=False,  # Less aggressive patching
        Event=False,
        builtins=True,
        signal=True
    ) 