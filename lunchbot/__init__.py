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
        conninfo=app.config['APP_DB_URL'],
        min_size=2,
        max_size=10,
        open=True,
        timeout=5,
    )
    app.extensions['pool'] = pool
    atexit.register(pool.close)
    logger.info('Connection pool initialized')

    # Initialize APScheduler for poll scheduling (Phase 5, D-08)
    from lunchbot.services.scheduler_service import init_scheduler
    init_scheduler(app)
    atexit.register(lambda: app.extensions.get('scheduler') and app.extensions['scheduler'].running and app.extensions['scheduler'].shutdown(wait=False))
    logger.info('Scheduler initialized')

    # Register middleware (Phase 2: multi-tenancy)
    from lunchbot.middleware.signature import verify_slack_signature
    from lunchbot.middleware.tenant import set_tenant_context
    app.before_request(verify_slack_signature)
    app.before_request(set_tenant_context)

    # Register blueprints (D-10)
    from lunchbot.blueprints.health import bp as health_bp
    from lunchbot.blueprints.slack_actions import bp as slack_bp
    from lunchbot.blueprints.polls import bp as polls_bp
    from lunchbot.blueprints.oauth import bp as oauth_bp
    from lunchbot.blueprints.events import bp as events_bp
    from lunchbot.blueprints.setup import bp as setup_bp
    app.register_blueprint(health_bp)
    app.register_blueprint(slack_bp)
    app.register_blueprint(polls_bp)
    app.register_blueprint(oauth_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(setup_bp)

    return app
