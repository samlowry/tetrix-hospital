from flask import Blueprint, jsonify, current_app
from sqlalchemy import text
from datetime import datetime
from models import Metrics, User, db
from utils.decorators import log_api_call

metrics = Blueprint('metrics', __name__)

async def update_metrics():
    """Update metrics in database"""
    try:
        # For now, we'll use a dummy value for holders
        holders = 420  # This will be updated with real calculation later
        
        metrics = Metrics.query.first()
        if not metrics:
            metrics = Metrics()
            db.session.add(metrics)
            
        metrics.holder_count = holders
        metrics.last_updated = datetime.utcnow()
        
        db.session.commit()
    except Exception as e:
        print(f"Error updating metrics: {e}")
        db.session.rollback()

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
      500:
        description: System is unhealthy
    """
    try:
        # Check database connection
        db.session.execute(text('SELECT 1'))
        
        # Check Redis connection
        redis_client = current_app.extensions['redis']
        redis_client.ping()
        
        # Check metrics
        metrics = Metrics.query.first()
        if not metrics:
            metrics = Metrics()
            db.session.add(metrics)
            db.session.commit()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'redis': 'connected',
            'last_metrics_update': metrics.last_updated.isoformat() if metrics.last_updated else None
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500 