"""Slack interactive action endpoints.

Handles: /action (vote clicks, suggestion select), /find_suggestions (external select search).
Phase 3 will wire these to the migrated service layer.
"""
import json
import logging

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

bp = Blueprint('slack_actions', __name__)


@bp.route('/action', methods=['POST'])
def action():
    """Handle Slack interactive actions (button clicks, external selects).
    Accepts same payload shape as the current Cloud Function.
    """
    payload = json.loads(request.form.get('payload', '{}'))
    logger.info('Received action type: %s', payload.get('type', 'unknown'))
    # Phase 3 wires to voter.vote() and suggestions.suggest()
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
