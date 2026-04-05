import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://localhost/lunchbot')
    SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
    SLACK_SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET')
    GOOGLE_PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY')

class DevConfig(Config):
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class TestConfig(Config):
    TESTING = True
    DATABASE_URL = os.environ.get('TEST_DATABASE_URL', 'postgresql://localhost/lunchbot_test')
    LOG_LEVEL = 'DEBUG'

class ProdConfig(Config):
    DEBUG = False
    LOG_LEVEL = 'WARNING'

config = {
    'dev': DevConfig,
    'test': TestConfig,
    'prod': ProdConfig,
}
