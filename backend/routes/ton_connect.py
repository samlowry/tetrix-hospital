from flask import Blueprint, jsonify, request, current_app
from services.ton_proof_service import TonProofService
from utils.decorators import limiter, log_api_call
from models import User, db
import jwt
import os
import asyncio
import logging

logger = logging.getLogger('tetrix')
bp = Blueprint('ton_connect', __name__, url_prefix='/api')
ton_proof_service = TonProofService()

@bp.route('/generate_payload', methods=['POST'])
@limiter.limit("100 per minute")
def generate_payload():
    """Generate a random payload for TON Proof."""
    payload = ton_proof_service.generate_payload()
    return jsonify({'payload': payload})

@bp.route('/check_proof', methods=['POST'])
@log_api_call
def check_proof():
    """Verify TON Connect proof, register user, and issue JWT token."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Get Telegram init data from headers
        tg_init_data = request.headers.get('X-Telegram-Init-Data')
        if not tg_init_data:
            return jsonify({'error': 'Missing Telegram init data'}), 400

        # First verify the proof
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

        # Start registration process in background
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(current_app.bot_manager.register_user(
                address=data['address'],
                tg_init_data=tg_init_data,
                proof=data['proof']
            ))
        finally:
            loop.close()

        return jsonify({'token': token})

    except Exception as e:
        logger.error(f"Error in check_proof: {e}")
        return jsonify({'error': str(e)}), 400 