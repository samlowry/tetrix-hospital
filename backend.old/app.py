import os
import json
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

import monkey  # This must be the first import

from config import (
    WEBHOOK_PATH, WEBHOOK_URL,
    REDIS_HOST, REDIS_PORT, REDIS_URL  # Import centralized Redis settings
)

from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from flask_talisman import Talisman
from flasgger import Swagger
from flask_caching import Cache
import redis
from werkzeug.exceptions import HTTPException
from contextlib import contextmanager
import telegram
import asyncio

from models import db, User
from routes import user_bp, ton_connect_bp
from utils import limiter, setup_logging
from bot_manager import BotManager
from ton_client import TonClient

# Initialize Flask app
app = Flask(__name__)

# Setup CORS
frontend_url = os.getenv('FRONTEND_URL')
if not frontend_url:
    logger.warning("FRONTEND_URL not set, defaulting to localhost")
    frontend_url = 'http://localhost:3000'

CORS(app, resources={
    r"/*": {
        "origins": [frontend_url],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "ngrok-skip-browser-warning"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Configure database
# Always use container names for services
db_url = 'postgresql+psycopg://tetrix:tetrixpass@postgres:5432/tetrix'
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add Redis configuration to app config
app.config['REDIS_HOST'] = REDIS_HOST
app.config['REDIS_PORT'] = REDIS_PORT
app.config['REDIS_URL'] = REDIS_URL

# Initialize extensions
db.init_app(app)

# Redis configuration
REDIS_CONFIG = {
    'host': REDIS_HOST,
    'port': REDIS_PORT,
    'db': 0,
    'socket_timeout': 10,
    'retry_on_timeout': True,
    'socket_connect_timeout': 10,
    'socket_keepalive': True,
    'health_check_interval': 15,
    'max_connections': 100,
    'decode_responses': False,
    'connection_pool': redis.ConnectionPool(
        max_connections=100,
        retry_on_timeout=True,
        socket_timeout=10,
        socket_connect_timeout=10,
        host=REDIS_HOST,
        port=REDIS_PORT
    )
}

# Initialize Redis client
redis_client = redis.Redis(**REDIS_CONFIG)

# Add Redis to Flask extensions
app.extensions['redis'] = redis_client

# Redis keys for bot state
REDIS_KEYS = {
    'bot': 'bot',
    'bot_state': 'bot:state',
    'bot_data': 'bot:data',
    'webhook_url': 'bot:webhook_url',
    'user_data': 'bot:user_data',
    'chat_data': 'bot:chat_data',
    'callback_data': 'bot:callback_data',
    'conversations': 'bot:conversations',
    'user_sessions': 'user_sessions',
}


def get_bot_state():
    """Get bot state from Redis"""
    state = redis_client.get(REDIS_KEYS['bot_state'])
    if not state:
        return None
    return state.decode('utf-8')


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
    'CACHE_REDIS_URL': REDIS_URL,  # Use centralized Redis URL
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_KEY_PREFIX': 'tetrix:cache:',
    'CACHE_OPTIONS': {
        'socket_timeout': REDIS_CONFIG['socket_timeout'],
        'socket_connect_timeout': REDIS_CONFIG['socket_connect_timeout'],
        'socket_keepalive': REDIS_CONFIG['socket_keepalive'],
        'retry_on_timeout': REDIS_CONFIG['retry_on_timeout']
    }
})
cache.init_app(app)
limiter.init_app(app)

logger = setup_logging()

# Configure security
is_development = os.getenv('FLASK_ENV') == 'development'
talisman = Talisman(
    app,
    force_https=False,  # Disable HTTPS redirection
    force_https_permanent=False,
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
    },
    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "name": "X-API-Key",
            "in": "header",
            "description": "API key for authentication (required only for /api/user/* endpoints)"
        }
    }
})

# Initialize TON client
ton_client = TonClient()

# Register blueprints
app.register_blueprint(ton_connect_bp)
app.register_blueprint(user_bp)

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
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


@contextmanager
def get_event_loop():
    """Context manager for handling event loops safely across requests"""
    loop = None
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        yield loop
    finally:
        if loop and not loop.is_closed():
            try:
                # Cancel all running tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                # Wait for tasks cancellation
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception as e:
                logger.error(f"Error cleaning up event loop: {e}")


def run_async(coro):
    """Helper to run coroutines safely"""
    with get_event_loop() as loop:
        return loop.run_until_complete(coro)


# Initialize event loop for the application
try:
    app_loop = asyncio.get_event_loop()
    if app_loop.is_closed():
        app_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(app_loop)
except RuntimeError:
    app_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(app_loop)


@app.route(WEBHOOK_PATH, methods=['POST'])
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
                try:
                    # Initialize both bot and application if needed
                    if not bot_manager.bot._initialized or not bot_manager.application._initialized:
                        logger.info("Bot or application not initialized, initializing now...")
                        await bot_manager.initialize()

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

                    logger.info("Processing update...")
                    await bot_manager.application.process_update(update)
                    logger.info("Update processed successfully")
                except Exception as e:
                    logger.error(f"Error processing update: {e}", exc_info=True)
                    raise

            run_async(process_update())
            app_loop.create_task(process_update())
            return 'ok'

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            logger.exception(e)
            return jsonify({"error": str(e)}), 500

    abort(403)


@app.errorhandler(404)
def not_found(error):
    # Don't log traceback for 404, just log the path
    logger.info(f"404 for path: {request.path}")
    return jsonify({
        'status': 'error',
        'message': 'Not found',
        'code': 404
    }), 404


@app.errorhandler(Exception)
def handle_error(error):
    # Log full traceback only for non-404 errors
    if not isinstance(error, HTTPException) or error.code != 404:
        logger.error(f"Unhandled error: {str(error)}", exc_info=True)

    code = 500
    if isinstance(error, HTTPException):
        code = error.code
    return jsonify({
        'status': 'error',
        'message': str(error),
        'code': code
    }), code


async def setup_telegram_webhook():
    """Setup Telegram webhook for receiving updates"""
    logger.info("Starting webhook setup...")
    if not WEBHOOK_URL:
        logger.error("WEBHOOK_URL not set in environment")
        return False

    logger.info(f"Using webhook URL: {WEBHOOK_URL}")
    try:
        # Check current webhook status
        logger.info("Getting current webhook info...")
        webhook_info = await bot_manager.bot.get_webhook_info()
        current_url = webhook_info.url
        target_url = WEBHOOK_URL  # URL already includes the path
        logger.info(f"Current webhook URL: {current_url}")
        logger.info(f"Target webhook URL: {target_url}")

        if current_url != target_url:
            # Only update webhook if URL is different
            logger.info("URLs are different, updating webhook...")
            await bot_manager.bot.delete_webhook(drop_pending_updates=True)
            await bot_manager.bot.set_webhook(
                url=target_url,
                drop_pending_updates=True
            )
            logger.info(f"Successfully set webhook to {target_url}")
            redis_client.set(REDIS_KEYS['webhook_url'], target_url)
        else:
            logger.info(f"Webhook URL is already correct ({current_url}), skipping update")

        return True
    except Exception as e:
        logger.error(f"Failed to set webhook: {str(e)}", exc_info=True)
        return False


def init_app(app):
    """Initialize the application"""
    logger.info("Starting application initialization...")
    with app.app_context():
        try:
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("Database tables created successfully")

            # Initialize bot and application
            logger.info("Initializing bot manager...")
            run_async(bot_manager.initialize())
            logger.info("Bot manager initialized successfully")

            # Setup webhook
            logger.info("Setting up Telegram webhook...")
            webhook_result = run_async(setup_telegram_webhook())
            logger.info(f"Webhook setup result: {webhook_result}")

            # Log final webhook status
            logger.info("Getting final webhook status...")
            webhook_info = run_async(bot_manager.bot.get_webhook_info())
            logger.info(f"Final webhook status - URL: {webhook_info.url}, Pending updates: {webhook_info.pending_update_count}")

            logger.info("Application initialization completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error during application initialization: {str(e)}", exc_info=True)
            raise


def on_starting(server):
    """Run before the server starts accepting requests"""
    logger.info("Running pre-start initialization...")
    try:
        init_app(app)
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}", exc_info=True)
        raise


# Initialize the app (for non-Gunicorn environments)
if not os.environ.get('GUNICORN_CMD_ARGS'):
    try:
        init_app(app)
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=False
    )
