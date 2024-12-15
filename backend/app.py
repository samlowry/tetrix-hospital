from flask import Flask, jsonify
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

from models import db, User
from routes import auth, user, metrics
from routes.metrics import update_metrics
from utils import limiter, setup_logging
from bot_manager import BotManager
from ton_client import TonClient

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)

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
limiter.init_app(app)
logger = setup_logging()

# Initialize Redis and Cache
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=int(os.getenv('REDIS_PORT', 6379))
)

cache = Cache(config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    'CACHE_DEFAULT_TIMEOUT': 300
})
cache.init_app(app)

# Setup CORS
cors_origins = os.getenv('CORS_ORIGINS', 'https://your-app.com').split(',')
CORS(app, resources={
    r"/*": {
        "origins": cors_origins,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
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
app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(user, url_prefix='/user')
app.register_blueprint(metrics, url_prefix='/')

# Initialize bot manager
bot_manager = BotManager(
    token=os.getenv('TELEGRAM_BOT_TOKEN'),
    db=db,
    User=User,
    ton_client=ton_client,
    app=app
)

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