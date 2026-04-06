"""Slack Events API endpoint.

Handles:
  - url_verification: Slack challenge for event subscription setup
  - app_uninstalled: Workspace removed the app
  - tokens_revoked: Workspace tokens invalidated
  - app_home_opened: Render settings panel for user

Both app_uninstalled and tokens_revoked call deactivate_workspace (idempotent).
app_home_opened builds and publishes the App Home view (T-05-06: admin gating).
"""
import logging
from flask import Blueprint, request, jsonify

from lunchbot.client.workspace_client import deactivate_workspace, get_workspace_settings
from lunchbot.client import slack_client
from lunchbot.services.app_home_service import build_home_view

logger = logging.getLogger(__name__)

bp = Blueprint('events', __name__, url_prefix='/slack')


def _is_workspace_admin(user_id, team_id):
    """Check if a Slack user is a workspace admin.

    Uses users.info API -- admin field is in user object.
    T-05-06: Non-admins see read-only App Home without edit buttons.
    """
    try:
        token = slack_client.get_bot_token(team_id)
        response = slack_client.session.get(
            slack_client.SLACK_API + "users.info",
            headers=slack_client._headers(token),
            params={'user': user_id}
        )
        data = response.json()
        if data.get('ok'):
            return data['user'].get('is_admin', False) or data['user'].get('is_owner', False)
    except Exception:
        logger.exception('Failed to check admin status for user %s', user_id)
    return False


@bp.route('/events', methods=['POST'])
def events():
    """Handle Slack Events API callbacks."""
    data = request.get_json(silent=True) or {}

    # Slack URL verification challenge
    if data.get('type') == 'url_verification':
        return jsonify({'challenge': data.get('challenge', '')})

    event = data.get('event', {})
    event_type = event.get('type')
    team_id = data.get('team_id')

    logger.info('Received Slack event: type=%s team_id=%s', event_type, team_id)

    if event_type in ('app_uninstalled', 'tokens_revoked'):
        if team_id:
            deactivate_workspace(team_id)
            logger.info('Handled %s for workspace %s', event_type, team_id)
        else:
            logger.warning('Received %s without team_id', event_type)

    if event_type == 'app_home_opened':
        user_id = event.get('user')
        if team_id and user_id:
            is_admin = _is_workspace_admin(user_id, team_id)
            settings = get_workspace_settings(team_id)
            view = build_home_view(settings, is_admin=is_admin)
            slack_client.views_publish(user_id, view, team_id)
            logger.info('Published App Home for user %s in workspace %s (admin=%s)',
                        user_id, team_id, is_admin)

    return '', 200
