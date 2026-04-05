import logging

from flask import Blueprint, jsonify, current_app

logger = logging.getLogger(__name__)

bp = Blueprint('health', __name__)


@bp.route('/health')
def health_check():
    """Health check -- verifies app is running and DB is reachable."""
    try:
        pool = current_app.extensions['pool']
        with pool.connection() as conn:
            conn.execute("SELECT 1")
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        logger.error('Health check failed: %s', e)
        return jsonify({"status": "unhealthy", "error": str(e)}), 503
