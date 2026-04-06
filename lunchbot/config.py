import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    LOG_RENDERER = 'console'
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://localhost/lunchbot')
    SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
    SLACK_SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET')
    GOOGLE_PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY')
    SLACK_CLIENT_ID = os.environ.get('SLACK_CLIENT_ID')
    SLACK_CLIENT_SECRET = os.environ.get('SLACK_CLIENT_SECRET')
    FERNET_KEY = os.environ.get('FERNET_KEY')
    SLACK_POLL_CHANNEL = os.environ.get('SLACK_POLL_CHANNEL', '')
    # lunchbot_app role URL — subject to RLS. Falls back to DATABASE_URL if not set.
    APP_DB_URL = os.environ.get('APP_DB_URL', DATABASE_URL)

    # Smart recommendations (Phase 4)
    # D-09: defaults POLL_SIZE=4, SMART_PICKS=2
    # D-10: overridable via env vars
    # D-11: single config for all workspaces
    # T-04-02: input validation — POLL_SIZE >= 1, SMART_PICKS clamped to [0, POLL_SIZE]
    POLL_SIZE = max(1, int(os.environ.get('POLL_SIZE', '4')))
    SMART_PICKS = min(
        max(0, int(os.environ.get('SMART_PICKS', '2'))),
        max(1, int(os.environ.get('POLL_SIZE', '4')))
    )

class DevConfig(Config):
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class TestConfig(Config):
    TESTING = True
    DATABASE_URL = os.environ.get('TEST_DATABASE_URL', 'postgresql://localhost/lunchbot_test')
    # Tests use superuser for pool so fixtures (TRUNCATE, etc.) work.
    # test_rls.py directly connects as lunchbot_app to verify RLS enforcement.
    APP_DB_URL = os.environ.get('TEST_DATABASE_URL', 'postgresql://localhost/lunchbot_test')
    LOG_LEVEL = 'DEBUG'
    # Disable Slack signature verification in tests; test_tenant_middleware.py tests
    # the verification logic directly with explicit signing secrets per test.
    SLACK_SIGNING_SECRET = None

class ProdConfig(Config):
    DEBUG = False
    LOG_LEVEL = 'INFO'
    LOG_RENDERER = 'json'

config = {
    'dev': DevConfig,
    'test': TestConfig,
    'prod': ProdConfig,
}
