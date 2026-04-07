import atexit
import logging
import uuid

import structlog
from flask import Flask
from prometheus_client import Counter, Gauge
from prometheus_flask_exporter import PrometheusMetrics
from psycopg_pool import ConnectionPool


def create_app(config_name='dev'):
    app = Flask(__name__)

    # Load config (D-09)
    from lunchbot.config import config
    app.config.from_object(config[config_name])

    # Configure structlog (D-01, D-04: structlog with dev/prod renderer switching)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if app.config.get('LOG_RENDERER') == 'json':
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Bridge stdlib logging through structlog (so existing logging.getLogger calls get structured)
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))

    logger = structlog.get_logger(__name__)

    # Initialize Prometheus metrics (D-08, D-09)
    metrics = PrometheusMetrics(app, path='/metrics')
    app.extensions['metrics'] = metrics

    # Custom business metrics (D-09)
    app.extensions['prom_polls_posted'] = Counter(
        'lunchbot_polls_posted_total',
        'Total polls posted',
        ['workspace_id'],
    )
    app.extensions['prom_votes_cast'] = Counter(
        'lunchbot_votes_cast_total',
        'Total votes cast',
        ['workspace_id'],
    )
    app.extensions['prom_scheduler_success'] = Counter(
        'lunchbot_scheduler_success_total',
        'Successful scheduled poll executions',
        ['workspace_id'],
    )
    app.extensions['prom_scheduler_failure'] = Counter(
        'lunchbot_scheduler_failure_total',
        'Failed scheduled poll executions',
        ['workspace_id'],
    )
    app.extensions['prom_scheduler_last_run'] = Gauge(
        'lunchbot_scheduler_last_run_timestamp',
        'Timestamp of last scheduler run per workspace',
        ['workspace_id'],
    )
    app.extensions['prom_db_pool_size'] = Gauge(
        'lunchbot_db_pool_size',
        'DB connection pool total size',
    )
    app.extensions['prom_db_pool_idle'] = Gauge(
        'lunchbot_db_pool_idle',
        'DB connection pool idle connections',
    )
    app.extensions['prom_db_pool_waiting'] = Gauge(
        'lunchbot_db_pool_waiting',
        'DB connection pool waiting requests',
    )

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
    logger.info('connection_pool_initialized')

    # Initialize APScheduler for poll scheduling (Phase 5, D-08)
    from lunchbot.services.scheduler_service import init_scheduler
    init_scheduler(app)
    atexit.register(lambda: app.extensions.get('scheduler') and app.extensions['scheduler'].running and app.extensions['scheduler'].shutdown(wait=False))
    logger.info('scheduler_initialized')

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

    from lunchbot.blueprints.web import bp as web_bp
    app.register_blueprint(web_bp)

    return app
