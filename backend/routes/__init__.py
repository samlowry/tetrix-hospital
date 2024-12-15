from .auth import auth as auth_bp
from .user import user as user_bp
from .metrics import metrics as metrics_bp
from .ton_connect import bp as ton_connect_bp

__all__ = ['auth_bp', 'user_bp', 'metrics_bp', 'ton_connect_bp'] 