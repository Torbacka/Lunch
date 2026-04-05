import atexit
import logging

from flask import Flask
from psycopg_pool import ConnectionPool


def create_app(config_name='dev'):
    app = Flask(__name__)

    # Load config (D-09)
    from lunchbot.config import config
    app.config.from_object(config[config_name])

    # Configure logging (D-11)
    logging.basicConfig(
        level=getattr(logging, app.config.get('LOG_LEVEL', 'INFO')),
        format='%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Initialize psycopg3 connection pool (D-05)
    pool = ConnectionPool(
        conninfo=app.config['DATABASE_URL'],
        min_size=2,
        max_size=10,
        open=True,
        timeout=5,
    )
    app.extensions['pool'] = pool
    atexit.register(pool.close)
    logger.info('Connection pool initialized')

    # Register blueprints (D-10)
    from lunchbot.blueprints.health import bp as health_bp
    from lunchbot.blueprints.slack_actions import bp as slack_bp
    from lunchbot.blueprints.polls import bp as polls_bp
    app.register_blueprint(health_bp)
    app.register_blueprint(slack_bp)
    app.register_blueprint(polls_bp)

    return app
