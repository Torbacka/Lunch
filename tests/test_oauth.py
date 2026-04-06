"""Tests for OAuth V2 install/callback flow.

Uses unit mocking for external calls (slack_sdk.web.WebClient).
DB tests use @pytest.mark.db and clean_all_tables fixture.
"""
import pytest
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet


# ---------------------------------------------------------------------------
# Test: install redirect
# ---------------------------------------------------------------------------

def test_install_redirects_to_slack(client, app):
    """GET /slack/install should redirect to Slack OAuth V2 authorize URL."""
    app.config['SLACK_CLIENT_ID'] = 'test-client-id'
    response = client.get('/slack/install')
    assert response.status_code == 302
    location = response.headers.get('Location', '')
    assert 'https://slack.com/oauth/v2/authorize' in location
    assert 'client_id=test-client-id' in location
    assert 'scope=commands' in location
    assert 'chat:write' in location
    assert 'users:read' in location


# ---------------------------------------------------------------------------
# Test: OAuth redirect success
# ---------------------------------------------------------------------------

def test_oauth_redirect_success(client, app):
    """GET /slack/oauth_redirect with valid code redirects to setup page."""
    fernet_key = Fernet.generate_key().decode()
    app.config['SLACK_CLIENT_ID'] = 'test-client-id'
    app.config['SLACK_CLIENT_SECRET'] = 'test-client-secret'
    app.config['FERNET_KEY'] = fernet_key

    mock_response = {
        'team': {'id': 'T_TEST', 'name': 'Test Team'},
        'access_token': 'xoxb-test-token',
        'bot_user_id': 'U_BOT',
        'scope': 'commands,chat:write,users:read',
    }

    with patch('lunchbot.blueprints.oauth.WebClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.oauth_v2_access.return_value = mock_response
        mock_client_class.return_value = mock_client

        with patch('lunchbot.blueprints.oauth.save_workspace'):
            response = client.get('/slack/oauth_redirect?code=test-code')

    assert response.status_code == 302
    assert '/slack/setup?team_id=T_TEST' in response.headers.get('Location', '')


# ---------------------------------------------------------------------------
# Test: OAuth redirect stores encrypted token (DB)
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_oauth_redirect_stores_encrypted_token(client, app, clean_all_tables):
    """OAuth callback stores encrypted (not plaintext) token in workspaces table."""
    fernet_key = Fernet.generate_key().decode()
    app.config['SLACK_CLIENT_ID'] = 'test-client-id'
    app.config['SLACK_CLIENT_SECRET'] = 'test-client-secret'
    app.config['FERNET_KEY'] = fernet_key

    mock_response = {
        'team': {'id': 'T_ENC', 'name': 'Enc Team'},
        'access_token': 'xoxb-test-token',
        'bot_user_id': 'U_BOT',
        'scope': 'commands,chat:write,users:read',
    }

    with patch('lunchbot.blueprints.oauth.WebClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.oauth_v2_access.return_value = mock_response
        mock_client_class.return_value = mock_client

        response = client.get('/slack/oauth_redirect?code=test-code')

    assert response.status_code == 302

    with app.app_context():
        from lunchbot.client.workspace_client import get_workspace
        from lunchbot.blueprints.oauth import decrypt_token
        ws = get_workspace('T_ENC')

    assert ws is not None
    assert ws['is_active'] is True
    assert ws['bot_token_encrypted'] != 'xoxb-test-token'
    assert decrypt_token(ws['bot_token_encrypted'], fernet_key) == 'xoxb-test-token'


# ---------------------------------------------------------------------------
# Test: success page content
# ---------------------------------------------------------------------------

def test_oauth_redirect_success_page_contains_heading(client, app):
    """Successful OAuth redirects to setup page with correct team_id."""
    fernet_key = Fernet.generate_key().decode()
    app.config['SLACK_CLIENT_ID'] = 'test-client-id'
    app.config['SLACK_CLIENT_SECRET'] = 'test-client-secret'
    app.config['FERNET_KEY'] = fernet_key

    mock_response = {
        'team': {'id': 'T_HDG', 'name': 'HDG Team'},
        'access_token': 'xoxb-test-token',
        'bot_user_id': 'U_BOT',
        'scope': 'commands,chat:write,users:read',
    }

    with patch('lunchbot.blueprints.oauth.WebClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.oauth_v2_access.return_value = mock_response
        mock_client_class.return_value = mock_client

        with patch('lunchbot.blueprints.oauth.save_workspace'):
            response = client.get('/slack/oauth_redirect?code=test-code')

    assert response.status_code == 302
    assert '/slack/setup?team_id=T_HDG' in response.headers.get('Location', '')


# ---------------------------------------------------------------------------
# Test: error page - missing code
# ---------------------------------------------------------------------------

def test_oauth_redirect_error_no_code(client, app):
    """GET /slack/oauth_redirect without code returns 400 and error page."""
    response = client.get('/slack/oauth_redirect')
    assert response.status_code == 400
    assert b'Installation Failed' in response.data


# ---------------------------------------------------------------------------
# Test: error page - error param
# ---------------------------------------------------------------------------

def test_oauth_redirect_error_param(client, app):
    """GET /slack/oauth_redirect?error=access_denied returns 400 and error page."""
    response = client.get('/slack/oauth_redirect?error=access_denied')
    assert response.status_code == 400
    assert b'Installation Failed' in response.data


# ---------------------------------------------------------------------------
# Test: Fernet round-trip
# ---------------------------------------------------------------------------

def test_fernet_roundtrip():
    """Fernet encrypt/decrypt round-trip preserves token value."""
    from lunchbot.blueprints.oauth import encrypt_token, decrypt_token
    key = Fernet.generate_key().decode()
    original = 'xoxb-test-token-abc123'
    encrypted = encrypt_token(original, key)
    assert encrypted != original
    decrypted = decrypt_token(encrypted, key)
    assert decrypted == original


# ---------------------------------------------------------------------------
# Test: reinstall reactivates workspace (DB)
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_reinstall_reactivates(client, app, clean_all_tables):
    """Reinstalling after uninstall reactivates workspace (is_active=True, uninstalled_at=None)."""
    fernet_key = Fernet.generate_key().decode()
    app.config['SLACK_CLIENT_ID'] = 'test-client-id'
    app.config['SLACK_CLIENT_SECRET'] = 'test-client-secret'
    app.config['FERNET_KEY'] = fernet_key

    # Initial install
    mock_response = {
        'team': {'id': 'T_REINST', 'name': 'Reinst Team'},
        'access_token': 'xoxb-test-token',
        'bot_user_id': 'U_BOT',
        'scope': 'commands,chat:write,users:read',
    }

    with patch('lunchbot.blueprints.oauth.WebClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.oauth_v2_access.return_value = mock_response
        mock_client_class.return_value = mock_client
        response = client.get('/slack/oauth_redirect?code=test-code')

    assert response.status_code == 302

    # Deactivate (simulate uninstall)
    with app.app_context():
        from lunchbot.client.workspace_client import deactivate_workspace, get_workspace
        deactivate_workspace('T_REINST')
        ws = get_workspace('T_REINST')
        assert ws['is_active'] is False

    # Reinstall
    with patch('lunchbot.blueprints.oauth.WebClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.oauth_v2_access.return_value = mock_response
        mock_client_class.return_value = mock_client
        response = client.get('/slack/oauth_redirect?code=test-code-2')

    assert response.status_code == 302

    with app.app_context():
        from lunchbot.client.workspace_client import get_workspace
        ws = get_workspace('T_REINST')
        assert ws['is_active'] is True
        assert ws['uninstalled_at'] is None
