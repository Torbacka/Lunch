"""Tests for the multi-tenant Slack API client."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_workspace_active():
    """Return an active workspace dict."""
    return {
        'id': 1,
        'team_id': 'T_TEST',
        'team_name': 'Test Team',
        'bot_token_encrypted': None,  # set per test
        'bot_user_id': 'U_BOT',
        'scopes': 'commands,chat:write',
        'is_active': True,
    }


@pytest.fixture
def fernet_key():
    """Generate a valid Fernet key for testing."""
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()


@pytest.fixture
def encrypted_token(fernet_key):
    """Encrypt a test token."""
    from lunchbot.blueprints.oauth import encrypt_token
    return encrypt_token('xoxb-test-bot-token', fernet_key)


class TestGetBotToken:
    """Tests for get_bot_token()."""

    def test_returns_decrypted_token(self, app, mock_workspace_active, fernet_key, encrypted_token):
        mock_workspace_active['bot_token_encrypted'] = encrypted_token
        app.config['FERNET_KEY'] = fernet_key
        with app.app_context():
            with patch('lunchbot.client.slack_client.get_workspace', return_value=mock_workspace_active):
                from lunchbot.client.slack_client import get_bot_token
                token = get_bot_token('T_TEST')
                assert token == 'xoxb-test-bot-token'

    def test_raises_for_missing_workspace(self, app, fernet_key):
        app.config['FERNET_KEY'] = fernet_key
        with app.app_context():
            with patch('lunchbot.client.slack_client.get_workspace', return_value=None):
                from lunchbot.client.slack_client import get_bot_token
                with pytest.raises(ValueError, match='No active workspace'):
                    get_bot_token('T_UNKNOWN')

    def test_raises_for_inactive_workspace(self, app, mock_workspace_active, fernet_key, encrypted_token):
        mock_workspace_active['bot_token_encrypted'] = encrypted_token
        mock_workspace_active['is_active'] = False
        app.config['FERNET_KEY'] = fernet_key
        with app.app_context():
            with patch('lunchbot.client.slack_client.get_workspace', return_value=mock_workspace_active):
                from lunchbot.client.slack_client import get_bot_token
                with pytest.raises(ValueError, match='No active workspace'):
                    get_bot_token('T_TEST')


class TestPostMessage:
    """Tests for post_message()."""

    def test_calls_chat_post_message(self, app, mock_workspace_active, fernet_key, encrypted_token):
        mock_workspace_active['bot_token_encrypted'] = encrypted_token
        app.config['FERNET_KEY'] = fernet_key
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ok': True, 'ts': '1234.5678'}

        with app.app_context():
            with patch('lunchbot.client.slack_client.get_workspace', return_value=mock_workspace_active), \
                 patch('lunchbot.client.slack_client.session') as mock_session:
                mock_session.post.return_value = mock_response
                from lunchbot.client.slack_client import post_message
                result = post_message('#general', [{'type': 'section'}], 'T_TEST', text='hello')

                mock_session.post.assert_called_once()
                call_args = mock_session.post.call_args
                assert 'chat.postMessage' in call_args[0][0]
                json_body = call_args[1]['json']
                assert json_body['channel'] == '#general'
                assert json_body['blocks'] == [{'type': 'section'}]
                assert json_body['text'] == 'hello'
                assert result == {'ok': True, 'ts': '1234.5678'}


class TestUpdateMessage:
    """Tests for update_message()."""

    def test_calls_chat_update(self, app, mock_workspace_active, fernet_key, encrypted_token):
        mock_workspace_active['bot_token_encrypted'] = encrypted_token
        app.config['FERNET_KEY'] = fernet_key
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ok': True}

        with app.app_context():
            with patch('lunchbot.client.slack_client.get_workspace', return_value=mock_workspace_active), \
                 patch('lunchbot.client.slack_client.session') as mock_session:
                mock_session.post.return_value = mock_response
                from lunchbot.client.slack_client import update_message
                result = update_message('#general', '1234.5678', [{'type': 'section'}], 'T_TEST')

                call_args = mock_session.post.call_args
                assert 'chat.update' in call_args[0][0]
                json_body = call_args[1]['json']
                assert json_body['channel'] == '#general'
                assert json_body['ts'] == '1234.5678'
                assert json_body['as_user'] is True
                assert result == {'ok': True}


class TestGetUserProfile:
    """Tests for get_user_profile()."""

    def test_returns_profile_dict(self, app, mock_workspace_active, fernet_key, encrypted_token):
        mock_workspace_active['bot_token_encrypted'] = encrypted_token
        app.config['FERNET_KEY'] = fernet_key
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ok': True,
            'user': {
                'profile': {'display_name': 'testuser', 'image_48': 'https://example.com/avatar.png'}
            }
        }

        with app.app_context():
            with patch('lunchbot.client.slack_client.get_workspace', return_value=mock_workspace_active), \
                 patch('lunchbot.client.slack_client.session') as mock_session:
                mock_session.get.return_value = mock_response
                from lunchbot.client.slack_client import get_user_profile
                profile = get_user_profile('U_USER', 'T_TEST')

                call_args = mock_session.get.call_args
                assert 'users.info' in call_args[0][0]
                params = call_args[1]['params']
                assert params['user'] == 'U_USER'
                assert profile == {'display_name': 'testuser', 'image_48': 'https://example.com/avatar.png'}
