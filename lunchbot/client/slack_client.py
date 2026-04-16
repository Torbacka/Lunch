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
    resp_json = response.json()
    if not resp_json.get('ok'):
        logger.error('chat.postMessage failed: %s', resp_json.get('error'))
    else:
        logger.info('Status code: %s response: %s', response.status_code, resp_json.get('ok'))
    return resp_json


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
    response = session.get(
        SLACK_API + "users.info",
        headers=_headers(token),
        params={'user': user_id}
    )
    data = response.json()
    if not data.get('ok'):
        logger.error('users.info failed for user=%s: %s', user_id, data.get('error', 'unknown'))
        return {}
    return data['user']['profile']


def views_publish(user_id, view, team_id):
    """Publish an App Home tab view for a user.

    Args:
        user_id: Slack user ID to publish the home tab for
        view: dict -- the view payload (type: 'home', blocks: [...])
        team_id: Slack team ID for token resolution

    Returns:
        Slack API response dict
    """
    token = get_bot_token(team_id)
    response = session.post(
        SLACK_API + "views.publish",
        headers=_headers(token),
        json={'user_id': user_id, 'view': view}
    )
    resp_json = response.json()
    if not resp_json.get('ok'):
        logger.error('views.publish failed: %s', resp_json.get('error'))
    return resp_json


def is_workspace_admin(user_id, team_id):
    """Return True iff the Slack user is an admin or owner of the workspace.

    Returns False on any error (least-privilege default — T-07.1-26).
    """
    try:
        token = get_bot_token(team_id)
        response = session.get(
            SLACK_API + "users.info",
            headers=_headers(token),
            params={'user': user_id},
        )
        data = response.json()
        if not data.get('ok'):
            return False
        u = data.get('user') or {}
        return bool(u.get('is_admin') or u.get('is_owner'))
    except Exception:
        logger.exception('is_workspace_admin failed for user=%s', user_id)
        return False


def list_bot_channels(team_id, cursor=None):
    """List channels the bot is a member of.

    Uses the users.conversations endpoint which returns only channels the
    caller (bot) has joined — satisfying D-16 (bot-member channels only,
    no extra filtering needed).

    Args:
        team_id: Slack team ID for workspace token resolution
        cursor: pagination cursor from a previous call, or None

    Returns:
        Tuple (channels, next_cursor) where channels is a list of dicts
        each containing at minimum 'id' and 'name', and next_cursor is
        the pagination cursor string or None when exhausted.
    """
    token = get_bot_token(team_id)
    params = {
        'types': 'public_channel,private_channel',
        'exclude_archived': 'true',
        'limit': '200',
    }
    if cursor:
        params['cursor'] = cursor
    response = session.get(
        SLACK_API + "users.conversations",
        headers=_headers(token),
        params=params,
    )
    data = response.json()
    if not data.get('ok'):
        logger.error('users.conversations failed: %s', data.get('error'))
        return ([], None)
    channels = [
        {'id': ch['id'], 'name': ch.get('name', '')}
        for ch in data.get('channels', [])
    ]
    next_cursor = (data.get('response_metadata') or {}).get('next_cursor') or None
    return (channels, next_cursor)


def views_open(trigger_id, view, team_id):
    """Open a modal view.

    Args:
        trigger_id: Slack trigger_id from the interaction payload
        view: dict -- the modal view payload
        team_id: Slack team ID for token resolution

    Returns:
        Slack API response dict
    """
    token = get_bot_token(team_id)
    response = session.post(
        SLACK_API + "views.open",
        headers=_headers(token),
        json={'trigger_id': trigger_id, 'view': view}
    )
    resp_json = response.json()
    if not resp_json.get('ok'):
        logger.error('views.open failed: %s', resp_json.get('error'))
    return resp_json
