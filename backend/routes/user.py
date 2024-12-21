from flask import Blueprint, jsonify, request, current_app
from models import User, db
from utils.decorators import limiter, log_api_call, require_api_key
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
from flasgger import swag_from

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

user = Blueprint('user', __name__, url_prefix='/api/user')

@user.route('/stats', methods=['POST'])
@log_api_call
@require_api_key
@swag_from({
    'tags': ['User'],
    'summary': 'Get user statistics',
    'description': 'Get detailed statistics for a user by their Telegram ID',
    'security': [
        {"ApiKeyAuth": []}
    ],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'telegram_id': {
                        'type': 'integer',
                        'description': 'Telegram user ID'
                    }
                },
                'required': ['telegram_id']
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'User statistics',
            'schema': {
                'type': 'object',
                'properties': {
                    'points': {'type': 'integer'},
                    'total_invites': {'type': 'integer'},
                    'registration_date': {'type': 'string', 'format': 'date-time'},
                    'points_breakdown': {
                        'type': 'object',
                        'properties': {
                            'holding': {'type': 'integer'},
                            'invites': {'type': 'integer'},
                            'early_backer_bonus': {'type': 'integer'}
                        }
                    },
                    'points_per_invite': {'type': 'integer'},
                    'invite_codes': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'code': {'type': 'string'},
                                'status': {'type': 'string', 'enum': ['active', 'used_today']}
                            }
                        }
                    },
                    'max_invite_slots': {'type': 'integer'},
                    'ignore_slot_reset': {'type': 'boolean'}
                }
            }
        },
        '400': {
            'description': 'Bad request',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        },
        '401': {
            'description': 'Invalid API key',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        },
        '404': {
            'description': 'User not found',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def get_user_stats():
    try:
        # Полчаем telegram_id из тела запроса
        data = request.get_json()
        if not data or 'telegram_id' not in data:
            return jsonify({'error': 'Telegram ID is required'}), 400
            
        telegram_id = data['telegram_id']
        
        # Ищем пользователя по telegram_id
        user = User.query.filter_by(telegram_id=telegram_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(user.get_stats())
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return jsonify({'error': str(e)}), 500

@user.route('/leaderboard/points', methods=['GET'])
@require_api_key
@swag_from({
    'tags': ['Leaderboard'],
    'summary': 'Get points leaderboard',
    'description': 'Get top users sorted by their total points',
    'security': [
        {"ApiKeyAuth": []}
    ],
    'parameters': [
        {
            'name': 'limit',
            'in': 'query',
            'type': 'integer',
            'description': 'Number of users to return (default: 10, max: 100)',
            'required': False
        }
    ],
    'responses': {
        '200': {
            'description': 'Points leaderboard',
            'schema': {
                'type': 'object',
                'properties': {
                    'leaderboard': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'telegram_name': {'type': 'string'},
                                'points': {'type': 'integer'},
                                'rank': {'type': 'integer'}
                            }
                        }
                    }
                }
            }
        },
        '401': {
            'description': 'Invalid API key',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def get_points_leaderboard():
    try:
        limit = min(int(request.args.get('limit', 10)), 100)
        users = User.query.all()
        
        # Получаем статистику для каждого пользователя и сортируем по points
        users_with_stats = [(user, user.get_stats()) for user in users]
        users_with_stats.sort(key=lambda x: x[1]['points'], reverse=True)
        users_with_stats = users_with_stats[:limit]
        
        return jsonify({
            'leaderboard': [{
                'telegram_name': stats['telegram_name'],
                'points': stats['points'],
                'rank': idx + 1
            } for idx, (user, stats) in enumerate(users_with_stats)]
        })
    except Exception as e:
        logger.error(f"Error getting points leaderboard: {e}")
        return jsonify({'error': str(e)}), 500

@user.route('/leaderboard/invites', methods=['GET'])
@require_api_key
@swag_from({
    'tags': ['Leaderboard'],
    'summary': 'Get invites leaderboard',
    'description': 'Get top users sorted by their successful invites count',
    'security': [
        {"ApiKeyAuth": []}
    ],
    'parameters': [
        {
            'name': 'limit',
            'in': 'query',
            'type': 'integer',
            'description': 'Number of users to return (default: 10, max: 100)',
            'required': False
        }
    ],
    'responses': {
        '200': {
            'description': 'Invites leaderboard',
            'schema': {
                'type': 'object',
                'properties': {
                    'leaderboard': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'telegram_name': {'type': 'string'},
                                'total_invites': {'type': 'integer'},
                                'rank': {'type': 'integer'}
                            }
                        }
                    }
                }
            }
        },
        '401': {
            'description': 'Invalid API key',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def get_invite_leaderboard():
    try:
        limit = min(int(request.args.get('limit', 10)), 100)
        
        # Get top inviters with their Telegram names
        top_inviters = User.get_top_inviters(limit)
        
        return jsonify({
            'leaderboard': [{
                'telegram_name': telegram_name,
                'total_invites': invite_count,
                'rank': idx + 1
            } for idx, (user, telegram_name, invite_count) in enumerate(top_inviters)]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500