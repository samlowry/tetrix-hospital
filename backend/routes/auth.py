from flask import Blueprint, request, jsonify
from nacl.signing import VerifyKey
from base64 import b64decode
import time
from models import User, db
from utils.decorators import limiter, log_api_call

auth = Blueprint('auth', __name__)
payloads = {}  # In-memory storage for payloads

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
    domain = "tetrix-hospital.pages.dev"
    timestamp = int(time.time())
    
    # Generate tonProof payload
    payload = {
        "type": "ton_proof",
        "domain": {
            "lengthBytes": len(domain),
            "value": domain
        },
        "timestamp": timestamp,
        "payload": f"Authorize with TETRIX at {timestamp}"
    }
    
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
        
        if not all([address, proof]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Verify proof
        payload = proof.get('payload')
        if not payload or payload not in payloads:
            return jsonify({'error': 'Invalid or expired payload'}), 400

        # Remove old payloads
        current_time = int(time.time())
        payloads_to_remove = [p for p, t in payloads.items() if current_time - t > 600]  # 10 minutes expiry
        for p in payloads_to_remove:
            payloads.pop(p)

        # Verify signature
        try:
            message = f"ton-proof-item-v2/{len(domain)}/{domain}/{address}/{proof['timestamp']}/{proof['payload']}"
            message_bytes = message.encode()
            signature = b64decode(proof['signature'])
            public_key = b64decode(proof['public_key'])
            
            verify_key = VerifyKey(public_key)
            verify_key.verify(message_bytes, signature)
        except Exception as e:
            return jsonify({'error': 'Invalid signature'}), 401

        # Remove used payload
        payloads.pop(payload)

        # Check if user exists
        existing_user = User.query.filter_by(wallet_address=address).first()
        if existing_user:
            return jsonify({'error': 'Wallet already registered'}), 400

        # Create new user
        user = User(wallet_address=address)
        user.points = 1000  # Starting points
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'points': user.points,
            'invite_code': user.invite_code
        })

    except Exception as e:
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
            
        # Verify proof
        domain = "tetrix-hospital.pages.dev"
        
        # Reconstruct message
        message = f"ton-proof-item-v2/{len(domain)}/{domain}/{address}/{proof['timestamp']}/{proof['payload']}"
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