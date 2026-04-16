import contextlib
import os
import pytest
from lunchbot.config import config as app_config

# Ensure test config is used
os.environ.setdefault('DATABASE_URL', app_config['test'].DATABASE_URL)


@pytest.fixture(scope='session')
def app():
    """Create Flask app with test config. Requires running PostgreSQL."""
    from lunchbot import create_app
    app = create_app('test')
    yield app
    # Pool closed via atexit


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Push app context for db_client calls."""
    with app.app_context():
        yield


@pytest.fixture
def clean_tables(app):
    """Truncate all tables before each test. Requires app context."""
    with app.app_context():
        pool = app.extensions['pool']
        with pool.connection() as conn:
            conn.execute("TRUNCATE votes, poll_options, polls, restaurants RESTART IDENTITY CASCADE")
        yield


@pytest.fixture
def clean_all_tables(app):
    """Truncate all tables including workspaces and channel_schedules."""
    with app.app_context():
        pool = app.extensions['pool']
        with pool.connection() as conn:
            conn.execute("TRUNCATE votes, poll_options, polls, restaurants, workspaces, channel_schedules RESTART IDENTITY CASCADE")
        yield


@pytest.fixture
def clean_all_tables_with_stats(app):
    """Truncate all tables including workspaces, restaurant_stats, and channel_schedules."""
    with app.app_context():
        pool = app.extensions['pool']
        with pool.connection() as conn:
            conn.execute("TRUNCATE votes, poll_options, polls, restaurants, workspaces, restaurant_stats, channel_schedules RESTART IDENTITY CASCADE")
        yield


@pytest.fixture
def workspace_a():
    """Workspace A test data."""
    return {'team_id': 'T_ALPHA', 'team_name': 'Alpha Team'}


@pytest.fixture
def workspace_b():
    """Workspace B test data."""
    return {'team_id': 'T_BRAVO', 'team_name': 'Bravo Team'}


@pytest.fixture
def tenant_connection(app):
    """Factory fixture: returns context manager for tenant-scoped DB connection."""
    @contextlib.contextmanager
    def _connect(workspace_id):
        with app.app_context():
            pool = app.extensions['pool']
            with pool.connection() as conn:
                # SET does not support parameterized values in PostgreSQL;
                # workspace_id is always an internal fixture value, not user input
                conn.execute(f"SET app.current_tenant = '{workspace_id}'")
                yield conn
    return _connect


@pytest.fixture
def sample_restaurant():
    """Sample restaurant dict matching Google Places API response shape."""
    return {
        'place_id': 'ChIJtest123',
        'name': 'Test Restaurant',
        'rating': 4.5,
        'price_level': 2,
        'geometry': {'location': {'lat': 59.3293, 'lng': 18.0686}},
        'photos': [{'photo_reference': 'abc123'}],
        'opening_hours': {'open_now': True},
        'icon': 'https://maps.google.com/icon.png',
        'vicinity': 'Test Street 1, Stockholm',
        'types': ['restaurant', 'food'],
        'user_ratings_total': 150,
    }
