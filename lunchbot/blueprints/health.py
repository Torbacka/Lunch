import time

import structlog
from flask import Blueprint, jsonify, current_app

logger = structlog.get_logger(__name__)

bp = Blueprint('health', __name__)

_start_time = time.monotonic()


@bp.route('/health')
def health_check():
    """Health check -- reports status, database, uptime, and pool stats.

    Per D-05: returns status, database (connected/disconnected),
    uptime_seconds, and db_pool (size, idle, waiting). No version field.
    """
    uptime_seconds = round(time.monotonic() - _start_time, 1)

    try:
        pool = current_app.extensions['pool']
        with pool.connection() as conn:
            conn.execute("SELECT 1")

        stats = pool.get_stats()
        db_pool = {
            'size': stats.get('pool_size', 0),
            'idle': stats.get('pool_available', 0),
            'waiting': stats.get('requests_waiting', 0),
        }

        # Update Prometheus pool gauges on each health check
        try:
            prom = current_app.extensions
            prom['prom_db_pool_size'].set(db_pool['size'])
            prom['prom_db_pool_idle'].set(db_pool['idle'])
            prom['prom_db_pool_waiting'].set(db_pool['waiting'])
        except KeyError:
            pass  # metrics not initialized (e.g., testing)

        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'uptime_seconds': uptime_seconds,
            'db_pool': db_pool,
        }), 200

    except Exception as e:
        logger.error('health_check_failed', error=str(e))
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'uptime_seconds': uptime_seconds,
            'error': str(e),
        }), 503
