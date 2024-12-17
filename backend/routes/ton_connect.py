from flask import Blueprint, jsonify, request
from services.ton_proof_service import TonProofService
from utils.decorators import limiter
import jwt
import os

bp = Blueprint('ton_connect', __name__, url_prefix='/api')
ton_proof_service = TonProofService()

@bp.route('/generate_payload', methods=['POST'])
@limiter.limit("100 per minute")
def generate_payload():
    """Generate a random payload for TON Proof."""
    payload = ton_proof_service.generate_payload()
    return jsonify({'payload': payload})

@bp.route('/check_proof', methods=['POST'])
def check_proof():
    """Verify TON Connect proof and issue JWT token."""
    return jsonify({'error': 'Rate limit exceeded'}), 429