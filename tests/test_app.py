"""Tests for Flask app creation and health check (INFRA-01, INFRA-02)."""
import warnings
import pytest


def test_create_app(app):
    """INFRA-01: App creates successfully on Python 3.12+ with Flask 3.x."""
    assert app is not None
    assert app.config['TESTING'] is True


def test_no_deprecation_warnings():
    """INFRA-02: No deprecation warnings at startup."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always", DeprecationWarning)
        from lunchbot import create_app
        try:
            app = create_app('test')
        except Exception:
            pass  # Connection errors are OK, we're checking imports
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, f"Deprecation warnings: {[str(x.message) for x in dep_warnings]}"


@pytest.mark.db
def test_health_check_returns_200(client):
    """INFRA-01: Health check responds 200 with database connectivity."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['database'] == 'connected'


@pytest.mark.db
def test_routes_registered(app):
    """All expected routes are registered in the app."""
    rules = [r.rule for r in app.url_map.iter_rules()]
    expected = ['/health', '/action', '/find_suggestions', '/lunch_message', '/suggestion_message', '/seed']
    for route in expected:
        assert route in rules, f"Route {route} not registered"


@pytest.mark.db
def test_action_endpoint_accepts_post(client):
    """Slack action endpoint accepts POST with form data."""
    response = client.post('/action', data={'payload': '{}'})
    assert response.status_code == 200


@pytest.mark.db
def test_find_suggestions_returns_options(client):
    """Find suggestions endpoint returns JSON with options array."""
    response = client.post('/find_suggestions', data={'payload': '{"value": "test"}'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'options' in data
