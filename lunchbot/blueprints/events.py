"""Slack Events API endpoint.

Handles:
  - url_verification: Slack challenge for event subscription setup
  - app_uninstalled: Workspace removed the app
  - tokens_revoked: Workspace tokens invalidated

Both app_uninstalled and tokens_revoked call deactivate_workspace (idempotent).
"""
import logging
from flask import Blueprint, request, jsonify

from lunchbot.client.workspace_client import deactivate_workspace

logger = logging.getLogger(__name__)

bp = Blueprint('events', __name__, url_prefix='/slack')


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

    if event_type in ('app_uninstalled', 'tokens_revoked'):
        if team_id:
            deactivate_workspace(team_id)
            logger.info('Handled %s for workspace %s', event_type, team_id)
        else:
            logger.warning('Received %s without team_id', event_type)

    return '', 200
