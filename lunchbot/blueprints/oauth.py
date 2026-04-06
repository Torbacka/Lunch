"""Slack OAuth V2 installation flow.

Endpoints:
  GET /slack/install -- redirect to Slack authorize URL
  GET /slack/oauth_redirect -- handle OAuth callback, store token
"""
import logging
from flask import Blueprint, redirect, request, current_app
from cryptography.fernet import Fernet
from slack_sdk.web import WebClient

from lunchbot.client.workspace_client import save_workspace

logger = logging.getLogger(__name__)

bp = Blueprint('oauth', __name__, url_prefix='/slack')

SCOPES = 'commands,chat:write,users:read'


def _redirect_uri():
    """Build the OAuth redirect URI, respecting X-Forwarded-Proto from reverse proxy."""
    scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
    return f'{scheme}://{request.host}/slack/oauth_redirect'


def encrypt_token(token, fernet_key):
    """Encrypt a bot token using Fernet symmetric encryption."""
    f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token, fernet_key):
    """Decrypt a bot token using Fernet symmetric encryption."""
    f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
    return f.decrypt(encrypted_token.encode()).decode()


@bp.route('/install')
def install():
    """Redirect to Slack OAuth V2 authorize URL."""
    client_id = current_app.config['SLACK_CLIENT_ID']
    redirect_uri = _redirect_uri()
    return redirect(
        f'https://slack.com/oauth/v2/authorize?client_id={client_id}&scope={SCOPES}&redirect_uri={redirect_uri}'
    )


@bp.route('/oauth_redirect')
def oauth_redirect():
    """Handle Slack OAuth V2 callback. Exchange code for token, store encrypted."""
    code = request.args.get('code')
    error = request.args.get('error')

    if error or not code:
        logger.warning('OAuth error: %s', error or 'no code')
        return _error_page(), 400

    try:
        redirect_uri = _redirect_uri()
        client = WebClient()
        response = client.oauth_v2_access(
            client_id=current_app.config['SLACK_CLIENT_ID'],
            client_secret=current_app.config['SLACK_CLIENT_SECRET'],
            code=code,
            redirect_uri=redirect_uri,
        )

        team_id = response['team']['id']
        team_name = response['team']['name']
        bot_token = response['access_token']
        bot_user_id = response.get('bot_user_id', '')
        scopes = response.get('scope', '')

        encrypted_token = encrypt_token(
            bot_token, current_app.config['FERNET_KEY']
        )

        save_workspace(
            team_id=team_id,
            team_name=team_name,
            bot_token_encrypted=encrypted_token,
            bot_user_id=bot_user_id,
            scopes=scopes,
        )

        logger.info('Workspace installed: %s (%s)', team_id, team_name)
        return _success_page()

    except Exception:
        logger.exception('OAuth token exchange failed')
        return _error_page(), 500


def _success_page():
    """Render OAuth success HTML per UI-SPEC."""
    return """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>LunchBot Installed</title>
<style>
body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 16px; background: #FFFFFF; }
.content { max-width: 480px; margin: 24px auto 0; }
h1 { font-size: 20px; font-weight: 600; color: #111827; line-height: 1.2; margin: 0 0 16px; }
p { font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5; margin: 0 0 16px; }
a { font-size: 16px; color: #4A154B; text-decoration: none; }
a:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="content">
<h1>LunchBot Installed</h1>
<p>LunchBot has been added to your workspace. You can close this tab and return to Slack to start using it.</p>
<a href="https://slack.com">Return to Slack</a>
</div>
</body>
</html>"""


def _error_page():
    """Render OAuth error HTML per UI-SPEC."""
    return """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Installation Failed</title>
<style>
body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 16px; background: #FFFFFF; }
.content { max-width: 480px; margin: 24px auto 0; }
h1 { font-size: 20px; font-weight: 600; color: #DC2626; line-height: 1.2; margin: 0 0 16px; }
p { font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5; margin: 0 0 16px; }
</style>
</head>
<body>
<div class="content">
<h1>Installation Failed</h1>
<p>Something went wrong connecting to your Slack workspace. Please try again from the Add to Slack button, or contact support if the problem persists.</p>
</div>
</body>
</html>"""
