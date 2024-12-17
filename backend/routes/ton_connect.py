from flask import Blueprint, jsonify, request
from services.ton_proof_service import TonProofService
from utils.decorators import limiter
from services.user_service import UserService
from services.telegram_service import TelegramService
import jwt
import os

bp = Blueprint('ton_connect', __name__, url_prefix='/api')
ton_proof_service = TonProofService()
user_service = UserService()
telegram_service = TelegramService()

@bp.route('/generate_payload', methods=['POST'])
@limiter.limit("100 per minute")
def generate_payload():
    """Generate a random payload for TON Proof."""
    payload = ton_proof_service.generate_payload()
    return jsonify({'payload': payload})

@bp.route('/check_proof', methods=['POST'])
def check_proof():
    """Verify TON Connect proof and issue JWT token."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        is_valid = ton_proof_service.check_proof(data)
        if not is_valid:
            return jsonify({'error': 'Invalid proof'}), 400

        address = data['address']
        is_early_backer = user_service.is_early_backer(address)

        # Generate JWT token
        token = jwt.encode(
            {
                'address': address,
                'network': data.get('network'),
                'public_key': data['public_key']
            },
            os.environ.get('JWT_SECRET_KEY', 'dev-secret-key'),
            algorithm='HS256'
        )

        if is_early_backer:
            # Register early backer and replace last message
            user_service.register_user(address, is_early_backer=True)
            return jsonify({
                'token': token,
                'status': 'early_backer',
                'message': 'Welcome, early backer! 🌟',
                'button': 'Continue to Stats',
                'replace_last': True
            })
        else:
            # Ask for invite code
            return jsonify({
                'token': token,
                'status': 'need_invite',
                'message': 'Please send invite code in chat',
                'replace_last': False
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 400