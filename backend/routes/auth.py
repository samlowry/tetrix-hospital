from flask import Blueprint, request, jsonify
from nacl.signing import VerifyKey
from base64 import b64decode
import time
from models import User, db
from utils.decorators import limiter, log_api_call
import logging
import os
from urllib.parse import urlparse

auth = Blueprint('auth', __name__)
payloads = {}  # In-memory storage for payloads

# Get domain from FRONTEND_URL
frontend_url = os.getenv('FRONTEND_URL')
if not frontend_url:
    logger.error("FRONTEND_URL not set")
    DOMAIN = 'localhost'
else:
    DOMAIN = urlparse(frontend_url).netloc

logger = logging.getLogger('tetrix')

@auth.route('/get-challenge', methods=['POST'])
@limiter.limit("10 per minute")
@log_api_call
def get_challenge():
    """
    Generate a challenge for wallet verification
    ---
    tags:
      - auth
    responses:
      200:
        description: Challenge generated successfully
      400:
        description: Invalid input
    """
    timestamp = int(time.time())
    
    # Generate tonProof payload
    payload = {
        "type": "ton_proof",
        "domain": {
            "lengthBytes": len(DOMAIN),
            "value": DOMAIN
        },
        "timestamp": timestamp,
        "payload": f"Authorize with TETRIX at {timestamp}"
    }
    
    logger.info(f"Generated payload: {payload}")
    logger.info(f"Current payloads before adding: {payloads}")
    payloads[payload['payload']] = timestamp
    logger.info(f"Current payloads after adding: {payloads}")
    
    return jsonify({"payload": payload})

@auth.route('/register-user', methods=['POST'])
@limiter.limit("5 per hour")
@log_api_call
def register_user():
    """Register user with TON Proof verification"""
    try:
        data = request.json
        address = data.get('address')
        proof = data.get('proof')
        invite_code = data.get('invite_code')  # Optional invite code
        
        logger.info(f"Received registration request - Address: {address}")
        logger.info(f"Received proof: {proof}")
        logger.info(f"Invite code: {invite_code}")

        if not all([address, proof]):
            logger.error("Missing required fields")
            return jsonify({'error': 'Missing required fields'}), 400

        # Verify proof
        payload = proof.get('payload')
        if not payload or payload not in payloads:
            logger.error(f"Invalid or expired payload. Payload: {payload}")
            return jsonify({'error': 'Invalid or expired payload'}), 400

        # Remove old payloads
        current_time = int(time.time())
        payloads_to_remove = [p for p, t in payloads.items() if current_time - t > 600]
        for p in payloads_to_remove:
            payloads.pop(p)

        # Verify signature
        try:
            message = f"ton-proof-item-v2/{len(DOMAIN)}/{DOMAIN}/{address}/{proof['timestamp']}/{proof['payload']}"
            message_bytes = message.encode()
            signature = b64decode(proof['signature'])
            public_key = b64decode(proof['public_key'])
            
            verify_key = VerifyKey(public_key)
            verify_key.verify(message_bytes, signature)
            logger.info("Signature verification successful")
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return jsonify({'error': 'Invalid signature'}), 401

        # Remove used payload
        payloads.pop(payload)

        # Check if user exists
        existing_user = User.query.filter_by(wallet_address=address).first()
        if existing_user:
            logger.error(f"Wallet already registered: {address}")
            return jsonify({'error': 'Wallet already registered'}), 400

        # Verify invite code if provided
        if invite_code:
            invite = User.verify_invite_code(invite_code)
            if not invite:
                logger.error(f"Invalid invite code: {invite_code}")
                return jsonify({'error': 'Invalid invite code'}), 400

        # Create new user
        user = User(wallet_address=address)
        db.session.add(user)
        db.session.commit()

        # Use invite code if provided
        if invite_code and invite:
            User.use_invite_code(invite_code, user.id)
            logger.info(f"Used invite code {invite_code} for user {user.id}")

        logger.info(f"Successfully registered new user with address: {address}")
        
        return jsonify({
            'status': 'success',
            'user_id': user.id
        })

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': str(e)}), 500

@auth.route('/check_proof', methods=['POST'])
@limiter.limit("10 per minute")
@log_api_call
def check_proof():
    """Verify TON Connect proof"""
    try:
        data = request.json
        address = data.get('address')
        proof = data.get('proof')
        
        if not all([address, proof]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Reconstruct message
        message = f"ton-proof-item-v2/{len(DOMAIN)}/{DOMAIN}/{address}/{proof['timestamp']}/{proof['payload']}"
        message_bytes = message.encode()
        
        # Verify signature
        signature = b64decode(proof['signature'])
        public_key = b64decode(proof['public_key'])
        
        verify_key = VerifyKey(public_key)
        try:
            verify_key.verify(message_bytes, signature)
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'error': 'Invalid signature'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400 