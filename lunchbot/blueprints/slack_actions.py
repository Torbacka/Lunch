"""Slack interactive action endpoints.

Handles: /action (vote clicks, suggestion select), /find_suggestions (external select search).
"""
import json
import logging

from flask import Blueprint, request, jsonify

from lunchbot.services import vote_service

logger = logging.getLogger(__name__)

bp = Blueprint('slack_actions', __name__)


@bp.route('/action', methods=['POST'])
def action():
    """Handle Slack interactive actions (button clicks, external selects).

    Routes button actions to vote_service for vote toggling.
    T-03-07: int() cast in vote_service catches malformed poll_option_id.
    """
    payload = json.loads(request.form.get('payload', '{}'))
    logger.info('Received action type: %s', payload.get('type', 'unknown'))

    actions = payload.get('actions', [])
    if actions and actions[0].get('type') == 'button':
        vote_service.vote(payload)

    return '', 200


@bp.route('/find_suggestions', methods=['POST'])
def find_suggestions():
    """Handle Slack external select search for restaurants.
    Accepts same payload shape as the current Cloud Function.
    """
    payload = json.loads(request.form.get('payload', '{}'))
    logger.info('Received suggestion search: %s', payload.get('value', ''))
    # Phase 3 wires to places_client + db_client.save_restaurants
    return jsonify({'options': []})
