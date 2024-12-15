from flask import Blueprint, jsonify, request
from backend.services.ton_proof_service import TonProofService
import jwt
import os

bp = Blueprint('ton_connect', __name__, url_prefix='/api')
ton_proof_service = TonProofService()

@bp.route('/generate_payload', methods=['POST'])
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

        # Generate JWT token
        token = jwt.encode(
            {
                'address': data['address'],
                'network': data.get('network'),
                'public_key': data['public_key']
            },
            os.environ.get('JWT_SECRET_KEY', 'dev-secret-key'),
            algorithm='HS256'
        )

        return jsonify({'token': token})

    except Exception as e:
        return jsonify({'error': str(e)}), 400 