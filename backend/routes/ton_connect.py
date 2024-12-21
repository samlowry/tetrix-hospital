from flask import Blueprint, jsonify, request
from services.ton_proof_service import TonProofService
from utils.decorators import limiter
from services.user_service import UserService
from services.telegram_service import TelegramService
import jwt
import os
from config import WEBHOOK_URL
from flasgger import swag_from

bp = Blueprint('ton_connect', __name__, url_prefix='/api')
ton_proof_service = TonProofService()
user_service = UserService()

@bp.route('/generate_payload', methods=['POST'])
@limiter.limit("100 per minute")
@swag_from({
    'tags': ['TON Connect'],
    'summary': 'Generate payload for TON Proof',
    'description': 'Generate a random payload that will be used for TON Connect proof. This endpoint is used by the frontend during wallet connection.',
    'responses': {
        '200': {
            'description': 'Generated payload',
            'schema': {
                'type': 'object',
                'properties': {
                    'payload': {'type': 'string'}
                }
            }
        }
    }
})
def generate_payload():
    """Generate a random payload for TON Proof."""
    payload = ton_proof_service.generate_payload()
    return jsonify({'payload': payload})

@bp.route('/check_proof', methods=['POST'])
@swag_from({
    'tags': ['TON Connect'],
    'summary': 'Verify TON Connect proof',
    'description': 'Verify TON Connect proof and register user. This endpoint is used by the frontend after getting proof from the wallet.',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'address': {'type': 'string', 'description': 'TON wallet address'},
                    'proof': {
                        'type': 'object',
                        'properties': {
                            'type': {'type': 'string', 'enum': ['ton_proof']},
                            'domain': {
                                'type': 'object',
                                'properties': {
                                    'lengthBytes': {'type': 'integer'},
                                    'value': {'type': 'string'}
                                }
                            },
                            'timestamp': {'type': 'integer'},
                            'payload': {'type': 'string'},
                            'signature': {'type': 'string'},
                            'state_init': {'type': 'string'},
                            'public_key': {'type': 'string'}
                        }
                    },
                    'tg_init_data': {'type': 'string', 'description': 'Telegram WebApp init data'}
                },
                'required': ['address', 'proof']
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Proof verification result',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'enum': ['registered', 'early_backer', 'need_invite']},
                    'message': {'type': 'string'},
                    'button': {'type': 'string'},
                    'replace_last': {'type': 'boolean'}
                }
            }
        },
        '400': {
            'description': 'Invalid proof or data',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def check_proof():
    """Verify TON Connect proof."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        is_valid = ton_proof_service.check_proof(data)
        if not is_valid:
            return jsonify({'error': 'Invalid proof'}), 400

        address = data['address']
        tg_init_data = data.get('tg_init_data')
        
        print(f"Received address: {address}")
        print(f"Checking if {address} is early backer...")
        is_early_backer = user_service.is_early_backer(address)
        print(f"Early backer status: {is_early_backer}")

        # Parse Telegram init data if provided
        telegram_id = None
        message_id = None
        if tg_init_data:
            try:
                from routes.user import parse_init_data
                init_data = parse_init_data(tg_init_data)
                telegram_id = init_data['user']['id']
                message_id = init_data.get('start_param')  # Get message_id from start_param
                print(f"Got Telegram ID: {telegram_id}")
            except Exception as e:
                print(f"Error parsing Telegram init data: {e}")
                # Don't fail if Telegram data is invalid, just log it

        # Check if user already exists
        existing_user = user_service.get_user_by_address(address)
        if existing_user:
            print(f"User {address} already registered")
            return jsonify({
                'status': 'registered',
                'message': 'Already registered',
                'replace_last': False
            })

        if is_early_backer:
            print(f"Registering early backer {address}...")
            # Register early backer and replace last message
            user_service.register_user(address, is_early_backer=True, telegram_id=telegram_id)
            print("Early backer registered successfully")

            # Show congratulations message if we have telegram_id
            if telegram_id:
                from flask import current_app
                import asyncio
                try:
                    # Get or create event loop
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Run the coroutine
                    loop.run_until_complete(current_app.bot_manager.show_congratulations(
                        telegram_id=telegram_id,
                        message_id=message_id,
                        is_early_backer=True
                    ))
                except Exception as e:
                    print(f"Error showing congratulations: {e}")

            return jsonify({
                'status': 'early_backer',
                'message': 'Welcome, early backer! 🌟',
                'button': 'Continue to Stats',
                'replace_last': True
            })
        else:
            print(f"User {address} needs invite code")
            # Register user without early backer status (not fully registered yet)
            user_service.register_user(address, is_early_backer=False, telegram_id=telegram_id)
            print(f"Registered user {address} without early backer status")
            
            # Ask for invite code and show appropriate message
            if telegram_id:
                from flask import current_app
                import asyncio
                try:
                    # Get or create event loop
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Run the coroutine
                    loop.run_until_complete(current_app.bot_manager.request_invite_code(
                        telegram_id=telegram_id,
                        message_id=message_id
                    ))
                except Exception as e:
                    print(f"Error requesting invite code: {e}")

            return jsonify({
                'status': 'need_invite',
                'message': 'Please send invite code in chat',
                'replace_last': False
            })

    except Exception as e:
        print(f"Error in check_proof: {e}")
        return jsonify({'error': str(e)}), 400