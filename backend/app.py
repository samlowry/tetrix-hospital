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

# Replace global flags with Redis
def is_initialized():
    return redis_client.get('app:initialized') == b'true'

def set_initialized():
    redis_client.set('app:initialized', 'true')

# Initialize bot at startup instead of per-request
async def initialize_bot():
    if not is_initialized():
        await setup_telegram_webhook()
        set_initialized()

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

async def setup_telegram_webhook():
    """Setup Telegram webhook for receiving updates"""
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        logger.error("WEBHOOK_URL not set in environment")
        return False
    
    try:
        await bot_manager.bot.initialize()
        await bot_manager.bot.delete_webhook()
        await bot_manager.bot.set_webhook(url=f"{webhook_url}/telegram-webhook")
        logger.info(f"Webhook set to {webhook_url}/telegram-webhook")
        return True
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        return False

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    if request.method == 'POST':
        try:
            json_data = request.get_json(force=True)
            
            async def process_update():
                await bot_manager.bot.initialize()
                update = telegram.Update.de_json(json_data, bot_manager.bot)
                await bot_manager.application.process_update(update)
            
            # Process update
            asyncio.run(process_update())
            return 'ok'
            
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}")
            logger.exception(e)  # Log full traceback
            return jsonify({"error": str(e)}), 500
    
    abort(403)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Initialize bot and start it
        asyncio.run(initialize_bot())
        asyncio.run(bot_manager.start_bot())
        
        # Run Flask app
        app.run(
            host=os.getenv('FLASK_HOST', '0.0.0.0'),
            port=int(os.getenv('FLASK_PORT', 5000)),
            debug=False
        ) 