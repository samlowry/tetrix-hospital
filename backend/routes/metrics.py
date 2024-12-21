from flask import Blueprint, jsonify, current_app
from sqlalchemy import text
from datetime import datetime
from models import Metrics, User, db
from utils.decorators import log_api_call

metrics = Blueprint('metrics', __name__)

@metrics.route('/metrics', methods=['GET'])
def get_metrics():
    metrics = Metrics.query.first()
    return jsonify({
        'holder_count': metrics.holder_count,
        'health': (metrics.holder_count / 100000) * 100
    })

@metrics.route('/health', methods=['GET'])
def health_check():
    """
    Check API health status
    ---
    tags:
      - system
    responses:
      200:
        description: System is healthy
      503:
        description: System is unhealthy
    """
    try:
        # Check database connection
        db.session.execute(text('SELECT 1'))
        db_status = True
    except Exception:
        db_status = False

    try:
        # Check Redis connection
        redis_client = current_app.extensions['redis']
        redis_client.ping()
        redis_status = True
    except Exception:
        redis_status = False

    checks = {
        'database': db_status,
        'redis': redis_status
    }

    response = {
        'status': 'healthy' if all(checks.values()) else 'unhealthy',
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    }

    return jsonify(response), 200 if all(checks.values()) else 503