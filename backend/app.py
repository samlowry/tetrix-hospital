from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from flask_talisman import Talisman
from flasgger import Swagger
from flask_caching import Cache
import redis
import os
from pathlib import Path
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
import asyncio
from werkzeug.exceptions import HTTPException
from contextlib import contextmanager
import telegram
from functools import partial
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram, Gauge
import json
import time

from models import db, User
from routes import auth_bp, user_bp, metrics_bp, ton_connect_bp
from routes.metrics import update_metrics
from utils import limiter, setup_logging
from bot_manager import BotManager
from ton_client import TonClient
from services.telegram_service import TelegramService

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / '.env'
print(f"Looking for .env at: {env_path.absolute()}")
if not env_path.exists():
    # Try current directory
    env_path = Path('.env')
    print(f"Not found, trying current directory: {env_path.absolute()}")
if env_path.exists():
    print(f"Found .env file at: {env_path.absolute()}")
    load_dotenv(env_path)
    print(f"Loaded TELEGRAM_BOT_TOKEN: {os.getenv('TELEGRAM_BOT_TOKEN')}")
else:
    print("No .env file found!")

# Initialize Flask app
app = Flask(__name__)

# Setup CORS
cors_origins = [
    'http://localhost:3000',
    'https://tetrix-hospital.pages.dev',
    'https://3bb1-109-245-96-58.ngrok-free.app'
]
CORS(app, resources={
    r"/*": {
        "origins": cors_origins,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "ngrok-skip-browser-warning"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Configure database
db_url = os.getenv('DATABASE_URL').replace('postgresql://', 'postgresql+psycopg://')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)

# Initialize Redis and Cache
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379))
)

# Add Redis to Flask extensions
app.extensions['redis'] = redis_client

# Redis keys for bot state
REDIS_KEYS = {
    'initialized': 'bot:initialized',
    'webhook_url': 'bot:webhook_url',
    'bot_state': 'bot:state',
    'user_sessions': 'bot:user_sessions:{}'  # Format with user_id
}

def get_bot_state():
    """Get bot state from Redis"""
    state = redis_client.get(REDIS_KEYS['bot_state'])
    return state.decode('utf-8') if state else None

def set_bot_state(state):
    """Set bot state in Redis"""
    redis_client.set(REDIS_KEYS['bot_state'], state)

def is_bot_initialized():
    """Check if bot is initialized"""
    return redis_client.get(REDIS_KEYS['initialized']) == b'true'

def set_bot_initialized():
    """Mark bot as initialized"""
    redis_client.set(REDIS_KEYS['initialized'], 'true')

def get_user_session(user_id):
    """Get user session from Redis"""
    session = redis_client.get(REDIS_KEYS['user_sessions'].format(user_id))
    return session.decode('utf-8') if session else None

def set_user_session(user_id, session_data):
    """Set user session in Redis"""
    redis_client.set(
        REDIS_KEYS['user_sessions'].format(user_id), 
        session_data,
        ex=3600  # 1 hour expiration
    )

# Configure cache
cache = Cache(config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'CACHE_DEFAULT_TIMEOUT': 300
})
cache.init_app(app)
limiter.init_app(app)

logger = setup_logging()

# Configure security
is_development = os.getenv('FLASK_ENV') == 'development'
Talisman(app,
    force_https=not is_development,
    content_security_policy={
        'default-src': "'self'",
        'img-src': '*',
        'script-src': ["'self'", "'unsafe-inline'"],
        'style-src': ["'self'", "'unsafe-inline'"]
    }
)

# Initialize Swagger documentation
swagger = Swagger(app, template={
    "info": {
        "title": "TETRIX Bot API",
        "description": "API for TETRIX Token Bot System",
        "version": "1.0.0"
    }
})

# Initialize TON client
ton_client = TonClient()

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(user_bp, url_prefix='/user')
app.register_blueprint(metrics_bp, url_prefix='/')
app.register_blueprint(ton_connect_bp)

# Initialize bot manager
bot_manager = BotManager(
    token=os.getenv('TELEGRAM_BOT_TOKEN'),
    db=db,
    User=User,
    ton_client=ton_client,
    app=app
)

# Add bot manager to app context
app.bot_manager = bot_manager

# Redis-based job store config
jobstores = {
    'default': RedisJobStore(
        jobs_key='scheduler.jobs',
        run_times_key='scheduler.runs',
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0))
    )
}

# Setup scheduler with Redis store
scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()

# Initialize Prometheus metrics
metrics = PrometheusMetrics(app)
requests_total = Counter('requests_total', 'Total requests')
request_latency = Histogram('request_latency_seconds', 'Request latency')
active_users = Gauge('active_users', 'Number of active users')

def check_db_connection():
    try:
        db.session.execute('SELECT 1')
        return True
    except Exception:
        return False

def check_redis_connection():
    try:
        redis_client.ping()
        return True
    except Exception:
        return False

def check_scheduler_status():
    return scheduler.running

@app.route('/health')
def health():
    checks = {
        'db': check_db_connection(),
        'redis': check_redis_connection(),
        'scheduler': check_scheduler_status()
    }
    status = all(checks.values())
    return jsonify({
        'status': 'healthy' if status else 'unhealthy',
        'checks': checks
    }), 200 if status else 503

def generate_webhook_secret():
    """Generate new webhook secret"""
    import secrets
    return secrets.token_urlsafe(32)

def get_webhook_secret():
    """Get webhook secret from Redis"""
    secret = redis_client.get(REDIS_KEYS['webhook_secret'])
    if not secret:
        secret = generate_webhook_secret().encode('utf-8')
        redis_client.set(REDIS_KEYS['webhook_secret'], secret)
    return secret.decode('utf-8')

@contextmanager
def webhook_lock(timeout=10):
    """Lock for webhook initialization"""
    lock_id = generate_webhook_secret()  # Используем как уникальный ID
    lock_timeout = timeout + 1
    
    # Try to acquire lock
    acquired = redis_client.set(
        REDIS_KEYS['webhook_lock'],
        lock_id,
        ex=lock_timeout,
        nx=True
    )
    
    try:
        yield acquired
    finally:
        # Release lock only if we acquired it and it's still ours
        if acquired and redis_client.get(REDIS_KEYS['webhook_lock']) == lock_id.encode('utf-8'):
            redis_client.delete(REDIS_KEYS['webhook_lock'])

async def setup_telegram_webhook():
    """Setup Telegram webhook for receiving updates"""
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        logger.error("WEBHOOK_URL not set in environment")
        return False
    
    try:
        # Check current webhook status
        webhook_info = await bot_manager.bot.get_webhook_info()
        current_url = webhook_info.url
        logger.info(f"Current webhook URL: {current_url}")
        
        # Always delete and recreate webhook to ensure clean state
        logger.info("Setting up webhook...")
        await bot_manager.bot.initialize()
        await bot_manager.bot.delete_webhook(drop_pending_updates=True)
        
        try:
            await bot_manager.bot.set_webhook(
                url=f"{webhook_url}/telegram-webhook",
                drop_pending_updates=True
            )
        except telegram.error.RetryAfter as e:
            logger.warning(f"Flood control, waiting {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
            await bot_manager.bot.set_webhook(
                url=f"{webhook_url}/telegram-webhook",
                drop_pending_updates=True
            )
        
        redis_client.set(REDIS_KEYS['webhook_url'], webhook_url)
        set_bot_initialized()
        logger.info(f"Webhook set to {webhook_url}/telegram-webhook")
        return True
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        return False

@contextmanager
def get_event_loop():
    """Context manager for handling event loops safely across requests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        try:
            # Cancel all running tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            # Wait for tasks cancellation
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

def run_async(coro):
    """Helper to run coroutines safely"""
    with get_event_loop() as loop:
        return loop.run_until_complete(coro)

# Initialize event loop for the application
app_loop = asyncio.new_event_loop()
asyncio.set_event_loop(app_loop)

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    if request.method == 'POST':
        try:
            json_data = request.get_json(force=True)
            # Get user_id from message or callback_query
            user_id = (
                json_data.get('message', {}).get('from', {}).get('id') or 
                json_data.get('callback_query', {}).get('from', {}).get('id')
            )
            logger.info(f"Processing update from user: {user_id}")
            
            async def process_update():
                update = telegram.Update.de_json(json_data, bot_manager.bot)
                
                # Store user session if needed
                if user_id:
                    session_data = json.dumps({
                        'last_activity': int(time.time()),
                        'update_type': (
                            update.effective_message.text if update.effective_message 
                            else update.callback_query.data if update.callback_query 
                            else None
                        )
                    })
                    set_user_session(user_id, session_data)
                
                await bot_manager.application.process_update(update)
            
            app_loop.run_until_complete(process_update())
            return 'ok'
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            logger.exception(e)
            return jsonify({"error": str(e)}), 500
    
    abort(403)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Initialize bot and start it
        app_loop.run_until_complete(setup_telegram_webhook())
        app_loop.run_until_complete(bot_manager.application.initialize())
        app_loop.run_until_complete(bot_manager.application.start())
        
        # Log final webhook status
        webhook_info = app_loop.run_until_complete(bot_manager.bot.get_webhook_info())
        logger.info(f"Final webhook status - URL: {webhook_info.url}, Pending updates: {webhook_info.pending_update_count}")
        
        # Run Flask app
        app.run(
            host=os.getenv('FLASK_HOST', '0.0.0.0'),
            port=int(os.getenv('FLASK_PORT', 5000)),
            debug=False
        ) 