from flask import Blueprint, jsonify, request
from flask_caching import Cache
from models import User, db
from utils.decorators import limiter, log_api_call
import os
import sys
import asyncio
from telegram import parse_init_data
from telegram.ext import Application

def normalize_address(address):
    # Remove '0:' prefix if present
    if address.startswith('0:'):
        address = address[2:]
    # Convert to uppercase and remove any non-hex characters
    return address.upper().strip()

user = Blueprint('user', __name__)
cache = Cache()

@user.route('/<wallet_address>/stats', methods=['GET'])
@log_api_call
def get_user_stats(wallet_address):
    user = User.query.filter_by(wallet_address=wallet_address).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.get_stats())

@user.route('/leaderboard/points', methods=['GET'])
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

@user.route('/leaderboard/invites', methods=['GET'])
@cache.cached(timeout=60)
def get_invite_leaderboard():
    try:
        limit = min(int(request.args.get('limit', 10)), 100)
        
        # Get top inviters
        top_inviters = User.get_top_inviters(limit)
        
        return jsonify({
            'leaderboard': [{
                'wallet_address': user.wallet_address,
                'total_invites': invite_count,
                'rank': idx + 1
            } for idx, (user, invite_count) in enumerate(top_inviters)]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user.route('/check_first_backer', methods=['POST'])
def check_first_backer():
    data = request.get_json()
    address = data.get('address')
    
    if not address:
        return jsonify({'error': 'Address is required'}), 400
        
    # Normalize the input address
    normalized_address = normalize_address(address)
    print(f"Checking address: {normalized_address}", file=sys.stderr)  # Debug log
        
    # Read first backers list
    try:
        with open('first_backers.txt', 'r') as f:
            # Normalize all addresses from the file
            first_backers = set(normalize_address(line.strip()) for line in f)
            
        is_first_backer = normalized_address in first_backers
        print(f"First backer status: {is_first_backer}", file=sys.stderr)  # Debug log
        return jsonify({'isFirstBacker': is_first_backer})
        
    except FileNotFoundError:
        return jsonify({'error': 'First backers list not found'}), 500

@user.route('/register_early_backer', methods=['POST'])
@log_api_call
def register_early_backer():
    try:
        data = request.get_json()
        address = data.get('address')
        tg_init_data = data.get('tg_init_data')
        
        if not all([address, tg_init_data]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Verify Telegram WebApp data
        try:
            init_data = parse_init_data(tg_init_data)
            telegram_id = init_data['user']['id']
        except Exception as e:
            logger.error(f"Invalid Telegram init data: {e}")
            return jsonify({'error': 'Invalid Telegram data'}), 400
            
        # Register user
        user = User.query.filter_by(wallet_address=address).first()
        if not user:
            user = User(wallet_address=address, telegram_id=telegram_id)
            user.points = 1000  # Early backer bonus
            db.session.add(user)
        else:
            user.telegram_id = telegram_id
            
        db.session.commit()
        
        # Trigger dashboard display
        asyncio.create_task(current_app.bot_manager.display_user_dashboard(telegram_id))
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error registering early backer: {e}")
        return jsonify({'error': str(e)}), 500