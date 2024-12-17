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
import asyncio
from werkzeug.exceptions import HTTPException
from contextlib import contextmanager
import telegram

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

# Add custom error handler
@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"Unhandled error: {str(error)}")
    
    if isinstance(error, HTTPException):
        response = {
            'error': error.description,
            'status_code': error.code
        }
        status_code = error.code
    else:
        response = {
            'error': 'Internal server error',
            'status_code': 500
        }
        status_code = 500
    
    return jsonify(response), status_code

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

# Setup CORS
cors_origins = [
    'http://localhost:3000',
    'https://tetrix-hospital.pages.dev',
    'https://5fa5-109-245-96-58.ngrok-free.app'
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

# Setup scheduler for metrics update
scheduler = BackgroundScheduler()

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def scheduled_metrics_update():
    """Wrapper for update_metrics with app context"""
    with app.app_context():
        await update_metrics()

# Schedule metrics update every 5 minutes
scheduler.add_job(
    lambda: run_async(scheduled_metrics_update()),
    'interval',
    minutes=5,
    max_instances=1,
    coalesce=True
)

@app.route('/telegram-webhook', methods=['POST'])
async def telegram_webhook():
    if request.method == 'POST':
        try:
            # Get update from Telegram
            update = telegram.Update.de_json(request.get_json(force=True), bot_manager.bot)
            
            # Process update
            await bot_manager.application.process_update(update)
            return 'ok'
            
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}")
            abort(500)
    
    abort(403)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        scheduler.start()
        # Start bot in a separate thread
        import threading
        bot_thread = threading.Thread(target=bot_manager.run)
        bot_thread.start()
        try:
            # Run Flask app
            app.run(
                host=os.getenv('FLASK_HOST', '0.0.0.0'),
                port=int(os.getenv('FLASK_PORT', 5000))
            )
        finally:
            # Clean shutdown
            bot_manager.stop()
            scheduler.shutdown()
            bot_thread.join() 