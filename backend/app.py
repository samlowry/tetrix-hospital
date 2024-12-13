from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import os
from typing import Optional
import secrets
from ton_client import TonClient
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import redis
import logging
from logging.handlers import RotatingFileHandler
from functools import wraps
from werkzeug.exceptions import HTTPException
from flask_cors import CORS
from flask_talisman import Talisman
from flasgger import Swagger
from bot_manager import BotManager

app = Flask(__name__)
# Use psycopg3 with SQLAlchemy 2.0
db_url = os.getenv('DATABASE_URL', 'postgresql+psycopg://tetrix:tetrixpass@localhost:5432/tetrix')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Test database connection
try:
    with app.app_context():
        db.session.execute('SELECT 1')
        print("Database connection successful!")
except SQLAlchemyError as e:
    print(f"Database connection failed: {e}")
    raise

# Initialize TON client
ton_client = TonClient()

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

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv('REDIS_URL', 'redis://redis:6379/0')
)

# Setup logging
def setup_logging():
    log_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] - %(message)s'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'tetrix.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(log_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    
    # Setup logger
    logger = logging.getLogger('tetrix')
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# Add decorator for logging API calls
def log_api_call(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            logger.info(f"API call: {f.__name__} - {request.remote_addr}")
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}")
            raise
    return decorated

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    wallet_address = db.Column(db.String(255), unique=True, nullable=False)
    points = db.Column(db.Integer, default=0)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    invite_slots = db.Column(db.Integer, default=5)
    invited_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    invite_code = db.Column(db.String(16), unique=True)
    last_slot_reset = db.Column(db.DateTime, default=datetime.utcnow)
    tetrix_balance = db.Column(db.Float, default=0)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.invite_code:
            self.invite_code = secrets.token_hex(8)

    def reset_slots_if_needed(self):
        """Reset invite slots daily"""
        today = datetime.utcnow().date()
        if self.last_slot_reset.date() < today:
            self.invite_slots = 5
            self.last_slot_reset = datetime.utcnow()
            return True
        return False

    def get_stats(self):
        """Get user statistics"""
        return {
            'points': self.points,
            'tetrix_balance': self.tetrix_balance,
            'invite_slots': self.invite_slots,
            'total_invites': User.query.filter_by(invited_by=self.id).count(),
            'registration_date': self.registration_date.isoformat(),
            'is_holder': self.tetrix_balance >= 1.0,
            'point_multiplier': max(1, int(self.tetrix_balance))  # 1x per TETRIX token
        }

    @classmethod
    def get_top_holders(cls, limit: int = 10):
        """Get top TETRIX token holders"""
        return cls.query.order_by(cls.tetrix_balance.desc()).limit(limit).all()
    
    @classmethod
    def get_top_inviters(cls, limit: int = 10):
        """Get users with most successful invites"""
        return db.session.query(
            cls,
            db.func.count(User.invited_by).label('invite_count')
        ).group_by(cls.id).order_by(
            db.text('invite_count DESC')
        ).limit(limit).all()

class Metrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    holder_count = db.Column(db.Integer, default=0)
    capitalization = db.Column(db.Float, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

# Initialize security and CORS
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",  # React dev server
            "https://your-app.com"    # Production URL
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
Talisman(app, 
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
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header"
        }
    }
})

# Core API endpoints
@app.route('/register-user', methods=['POST'])
@limiter.limit("5 per hour")
@log_api_call
def register_user():
    """
    Register a new user with wallet
    ---
    tags:
      - users
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - wallet_address
          properties:
            wallet_address:
              type: string
              description: TON wallet address
            invite_code:
              type: string
              description: Optional invite code
    responses:
      200:
        description: User registered successfully
      400:
        description: Invalid input
      500:
        description: Server error
    """
    data = request.json
    wallet = data.get('wallet_address')
    invite_code = data.get('invite_code')
    
    if not wallet:
        return jsonify({'error': 'Wallet address required'}), 400
        
    # Check if user already exists
    existing_user = User.query.filter_by(wallet_address=wallet).first()
    if existing_user:
        return jsonify({'error': 'Wallet already registered'}), 400
    
    # Validate invite code
    inviter = None
    if invite_code:
        inviter = User.query.filter_by(invite_code=invite_code).first()
        if not inviter:
            return jsonify({'error': 'Invalid invite code'}), 400
        if inviter.invite_slots <= 0:
            return jsonify({'error': 'Inviter has no slots available'}), 400
        
        # Reset inviter slots if needed
        inviter.reset_slots_if_needed()
        if inviter.invite_slots <= 0:
            return jsonify({'error': 'Inviter has no slots available'}), 400
            
        inviter.invite_slots -= 1
        inviter.points += 1000  # Reward for inviting
    
    # Create new user
    user = User(wallet_address=wallet)
    user.points = 2000 if inviter else 1000  # Extra points if invited
    if inviter:
        user.invited_by = inviter.id
    
    try:
        db.session.add(user)
        if inviter:
            db.session.add(inviter)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'points': user.points,
            'invite_code': user.invite_code
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/get-metrics', methods=['GET'])
def get_metrics():
    metrics = Metrics.query.first()
    return jsonify({
        'holder_count': metrics.holder_count,
        'health': (metrics.holder_count / 100000) * 100,
        'capitalization': metrics.capitalization
    })

# Add new endpoint for balance checking
@app.route('/check-balance/<wallet_address>', methods=['GET'])
async def check_balance(wallet_address):
    try:
        tetrix_balance = await ton_client.get_tetrix_balance(wallet_address)
        
        user = User.query.filter_by(wallet_address=wallet_address).first()
        if user:
            user.tetrix_balance = tetrix_balance
            db.session.commit()
            
        return jsonify({
            'tetrix_balance': tetrix_balance,
            'is_holder': tetrix_balance >= 1.0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add metrics update function
async def update_metrics():
    try:
        # Get all users with TETRIX balance
        holders = User.query.filter(User.tetrix_balance >= 1.0).count()
        
        # Calculate total capitalization (placeholder)
        total_cap = sum([user.tetrix_balance for user in User.query.all()])
        
        metrics = Metrics.query.first()
        if not metrics:
            metrics = Metrics()
            db.session.add(metrics)
            
        metrics.holder_count = holders
        metrics.capitalization = total_cap
        metrics.last_updated = datetime.utcnow()
        
        db.session.commit()
    except Exception as e:
        print(f"Error updating metrics: {e}")
        db.session.rollback()

# Setup scheduler for metrics update
scheduler = BackgroundScheduler()
scheduler.add_job(update_metrics, 'interval', minutes=5)

# Add new endpoints
@app.route('/user/<wallet_address>/stats', methods=['GET'])
def get_user_stats(wallet_address):
    user = User.query.filter_by(wallet_address=wallet_address).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.get_stats())

@app.route('/transfer-token', methods=['POST'])
async def transfer_token():
    data = request.json
    to_address = data.get('to_address')
    amount = data.get('amount', 1.0)
    
    if not to_address:
        return jsonify({'error': 'Recipient address required'}), 400
        
    try:
        # Attempt token transfer
        success = await ton_client.transfer_tetrix(to_address, amount)
        if success:
            # Update user balance
            user = User.query.filter_by(wallet_address=to_address).first()
            if user:
                user.tetrix_balance += amount
                db.session.commit()
            
            return jsonify({'status': 'success', 'amount': amount})
        else:
            return jsonify({'error': 'Transfer failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add new endpoints for leaderboards
@app.route('/leaderboard/points', methods=['GET'])
@cache.cached(timeout=60)  # Cache for 1 minute
def get_points_leaderboard():
    try:
        limit = min(int(request.args.get('limit', 10)), 100)
        users = User.query.order_by(User.points.desc()).limit(limit).all()
        
        return jsonify({
            'leaderboard': [{
                'wallet_address': user.wallet_address,
                'points': user.points,
                'rank': idx + 1
            } for idx, user in enumerate(users)]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/leaderboard/invites', methods=['GET'])
@cache.cached(timeout=60)
def get_invite_leaderboard():
    try:
        limit = min(int(request.args.get('limit', 10)), 100)
        
        # Subquery to count invites per user
        invite_counts = db.session.query(
            User.id,
            db.func.count(User.invited_by).label('invite_count')
        ).group_by(User.id).subquery()
        
        # Get top inviters
        top_inviters = db.session.query(
            User,
            invite_counts.c.invite_count
        ).join(
            invite_counts,
            User.id == invite_counts.c.id
        ).order_by(
            invite_counts.c.invite_count.desc()
        ).limit(limit).all()
        
        return jsonify({
            'leaderboard': [{
                'wallet_address': user.wallet_address,
                'total_invites': invite_count,
                'rank': idx + 1
            } for idx, (user, invite_count) in enumerate(top_inviters)]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add webhook handler for transaction notifications
@app.route('/webhook/transaction', methods=['POST'])
@limiter.limit("100 per minute")
async def transaction_webhook():
    data = request.json
    
    try:
        tx_hash = data.get('tx_hash')
        from_address = data.get('from_address')
        to_address = data.get('to_address')
        amount = float(data.get('amount', 0))
        
        if not all([tx_hash, from_address, to_address, amount]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Verify transaction
        tx_status = await ton_client.check_transaction_status(tx_hash)
        if not tx_status:
            return jsonify({'error': 'Invalid transaction'}), 400
            
        # Update balances
        sender = User.query.filter_by(wallet_address=from_address).first()
        recipient = User.query.filter_by(wallet_address=to_address).first()
        
        if sender:
            sender.tetrix_balance = max(0, sender.tetrix_balance - amount)
        if recipient:
            recipient.tetrix_balance += amount
            
        # Trigger metrics update
        await update_metrics()
        
        db.session.commit()
        # Clear leaderboard caches on successful transaction
        cache.delete('leaderboard/points')
        cache.delete('leaderboard/invites')
        return jsonify({'status': 'success'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

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

# Add health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """
    Check API health status
    ---
    tags:
      - system
    responses:
      200:
        description: System is healthy
      500:
        description: System is unhealthy
    """
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check Redis connection
        redis_client.ping()
        
        # Check metrics
        metrics = Metrics.query.first()
        if not metrics:
            metrics = Metrics()
            db.session.add(metrics)
            db.session.commit()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'redis': 'connected',
            'last_metrics_update': metrics.last_updated.isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# Add bot manager
bot_manager = BotManager(
    token=os.getenv('TELEGRAM_BOT_TOKEN'),
    db=db,
    User=User,
    ton_client=ton_client
)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        scheduler.start()
        # Start bot in a separate thread
        import threading
        bot_thread = threading.Thread(target=bot_manager.run)
        bot_thread.start()
        # Run Flask app
        app.run(host='0.0.0.0', port=5000) 