"""Per-workspace Slack API client.

Multi-tenant replacement for service/client/slack_client.py.
Every function takes team_id and resolves the workspace bot token
via get_workspace() + decrypt_token().

Threat mitigations:
  T-03-01: Never log decrypted tokens; log only team_id at DEBUG level
  T-03-02: Never log full headers dict (contains Authorization secret)
"""
import logging

import requests
from flask import current_app

from lunchbot.client.workspace_client import get_workspace
from lunchbot.blueprints.oauth import decrypt_token

logger = logging.getLogger(__name__)

SLACK_API = "https://slack.com/api/"

session = requests.Session()


def get_bot_token(team_id):
    """Resolve and decrypt bot token for a workspace.

    Raises ValueError if workspace not found or inactive.
    """
    workspace = get_workspace(team_id)
    if workspace is None or not workspace.get('is_active'):
        raise ValueError(f"No active workspace: {team_id}")
    fernet_key = current_app.config['FERNET_KEY']
    logger.debug('Decrypting bot token for team_id=%s', team_id)
    return decrypt_token(workspace['bot_token_encrypted'], fernet_key)


def _headers(token):
    """Build Authorization headers for Slack API calls."""
    return {
        'Content-Type': 'application/json;charset=utf-8',
        'Authorization': f'Bearer {token}'
    }


def _form_headers(token):
    """Build headers for form-encoded Slack API calls."""
    return {
        'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
        'Authorization': f'Bearer {token}'
    }


def post_message(channel, blocks, team_id, text=''):
    """Post a message to a Slack channel.

    Args:
        channel: Slack channel ID or name
        blocks: List of Block Kit block dicts
        team_id: Slack team ID for workspace token resolution
        text: Fallback text for notifications

    Returns:
        Slack API response as dict
    """
    token = get_bot_token(team_id)
    response = session.post(
        SLACK_API + "chat.postMessage",
        headers=_headers(token),
        json={'channel': channel, 'blocks': blocks, 'text': text}
    )
    logger.info('Status code: %s response: %s', response.status_code, response.json().get('ok'))
    return response.json()


def update_message(channel, ts, blocks, team_id):
    """Update an existing Slack message.

    Args:
        channel: Slack channel ID
        ts: Message timestamp to update
        blocks: Updated Block Kit blocks
        team_id: Slack team ID for workspace token resolution

    Returns:
        Slack API response as dict
    """
    token = get_bot_token(team_id)
    response = session.post(
        SLACK_API + "chat.update",
        headers=_headers(token),
        json={'channel': channel, 'ts': ts, 'blocks': blocks, 'as_user': True}
    )
    logger.info('Status code: %s response: %s', response.status_code, response.json().get('ok'))
    return response.json()


def get_user_profile(user_id, team_id):
    """Get a Slack user's profile.

    Args:
        user_id: Slack user ID
        team_id: Slack team ID for workspace token resolution

    Returns:
        Profile dict from Slack API
    """
    token = get_bot_token(team_id)
    response = session.post(
        SLACK_API + "users.profile.get",
        headers=_form_headers(token),
        data={'user': user_id}
    )
    logger.info('Status code: %s response: %s', response.status_code, response.json().get('ok'))
    return response.json()['profile']
