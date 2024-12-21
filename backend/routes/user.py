from flask import Blueprint, jsonify, request, current_app
from flask_caching import Cache
from models import User, db
from utils.decorators import limiter, log_api_call
from services.ton_proof_service import TON_PROOF_PREFIX, TON_CONNECT_PREFIX, TonProofService
from tonsdk.utils import Address
import os
import sys
import asyncio
import logging
import hashlib
import hmac
import json
from urllib.parse import parse_qs, urlparse
from base64 import b64decode
import nacl.signing

logger = logging.getLogger('tetrix')

# Get domain from FRONTEND_URL
frontend_url = os.getenv('FRONTEND_URL')
if not frontend_url:
    logger.error("FRONTEND_URL not set")
    DOMAIN = 'localhost'
else:
    DOMAIN = urlparse(frontend_url).netloc

def parse_init_data(init_data: str) -> dict:
    """Parse and validate Telegram WebApp init data"""
    try:
        # Get bot token from environment
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            raise ValueError("Bot token not found")

        # Parse the data
        parsed_data = dict(parse_qs(init_data))
        data_check_string = '\n'.join(
            f'{k}={v[0]}' for k, v in sorted(parsed_data.items()) if k != 'hash'
        )

        # Calculate secret key
        secret_key = hmac.new(
            'WebAppData'.encode(),
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        # Calculate data hash
        data_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Verify hash
        if data_hash != parsed_data.get('hash', [None])[0]:
            raise ValueError("Invalid hash")

        # Parse user data
        user_data = json.loads(parsed_data.get('user', ['{}'])[0])
        return {'user': user_data}

    except Exception as e:
        logger.error(f"Error parsing init data: {e}")
        raise ValueError("Invalid init data")

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