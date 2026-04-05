import os
import pytest
from lunchbot.config import config as app_config

@pytest.fixture(scope='session')
def test_database_url():
    return app_config['test'].DATABASE_URL

@pytest.fixture(scope='session')
def alembic_ini_path():
    return os.path.join(os.path.dirname(__file__), '..', 'migrations', 'alembic.ini')
