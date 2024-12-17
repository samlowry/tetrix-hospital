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
from urllib.parse import parse_qs
from base64 import b64decode
import nacl.signing

logger = logging.getLogger('tetrix')
DOMAIN = os.getenv('DOMAIN', 'localhost')  # Default to localhost if not set

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
        proof = data.get('proof')  # Get TON Proof
        
        logger.info(f"Received registration request for address: {address}")
        logger.info(f"Telegram init data received: {tg_init_data[:100]}...")  # Log first 100 chars
        
        if not all([address, tg_init_data, proof]):
            logger.error("Missing fields - Address, init_data, or proof")
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Verify TON Proof using the service
        try:
            # Prepare proof payload for verification
            proof_payload = {
                'address': address,
                'proof': {
                    'timestamp': proof['timestamp'],
                    'domain': {
                        'lengthBytes': len(DOMAIN),
                        'value': DOMAIN
                    },
                    'signature': proof['signature'],
                    'payload': proof['payload'],
                    'state_init': proof['state_init']
                },
                'public_key': proof['public_key']
            }
            
            if not TonProofService.check_proof(proof_payload):
                logger.error("TON Proof verification failed")
                return jsonify({'error': 'Invalid TON Proof'}), 401
            logger.info("TON Proof verification successful")
        except Exception as e:
            logger.error(f"TON Proof verification failed: {e}")
            return jsonify({'error': 'Invalid TON Proof'}), 401
            
        # Verify Telegram WebApp data
        try:
            init_data = parse_init_data(tg_init_data)
            telegram_id = init_data['user']['id']
            message_id = init_data.get('start_param')  # Get message_id from start_param
            logger.info(f"Successfully parsed init data. Telegram ID: {telegram_id}, Message ID: {message_id}")
        except Exception as e:
            logger.error(f"Invalid Telegram init data: {e}")
            return jsonify({'error': 'Invalid Telegram data'}), 400
            
        # Check if early backer
        normalized_address = normalize_address(address)
        try:
            with open('first_backers.txt', 'r') as f:
                first_backers = set(normalize_address(line.strip()) for line in f)
                is_early_backer = normalized_address in first_backers
        except FileNotFoundError:
            logger.warning("first_backers.txt not found, assuming not an early backer")
            is_early_backer = False
            
        # Register user
        user = User.query.filter_by(wallet_address=address).first()
        if not user:
            logger.info(f"Creating new user for address {address}")
            user = User(wallet_address=address, telegram_id=telegram_id)
            db.session.add(user)
        else:
            logger.info(f"Updating existing user {address} with telegram_id {telegram_id}")
            user.telegram_id = telegram_id
            
        db.session.commit()
        logger.info(f"User saved to database successfully")
        
        # Show appropriate message based on early backer status
        logger.info(f"Showing message for telegram_id {telegram_id}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if is_early_backer:
                # Show congratulations for early backer
                loop.run_until_complete(current_app.bot_manager.show_congratulations(
                    telegram_id=telegram_id,
                    message_id=message_id,
                    is_early_backer=True
                ))
            else:
                # Show invite code request for regular user
                loop.run_until_complete(current_app.bot_manager.request_invite_code(
                    telegram_id=telegram_id,
                    message_id=message_id
                ))
        finally:
            loop.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        return jsonify({'error': str(e)}), 500