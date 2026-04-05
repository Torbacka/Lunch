"""Poll management endpoints.

Handles: /lunch_message (trigger poll), /suggestion_message (send suggestion),
         /emoji (update emoji tags).
Phase 3 will wire these to the migrated service layer.
"""
import logging

from flask import Blueprint

logger = logging.getLogger(__name__)

bp = Blueprint('polls', __name__)


@bp.route('/lunch_message')
def lunch_message():
    """Trigger lunch poll message to Slack channel.
    Phase 3 wires to suggestions.push_suggestions().
    """
    logger.info('Lunch message triggered')
    # Phase 3 wires to suggestions.push_suggestions()
    return '', 200


@bp.route('/suggestion_message')
def suggestion_message():
    """Send suggestion template message to Slack channel.
    Phase 3 wires to slack_client.post_message().
    """
    logger.info('Suggestion message triggered')
    # Phase 3 wires to slack_client.post_message()
    return '', 200


@bp.route('/emoji', methods=['GET'])
def emoji():
    """Update emoji tags on restaurants.
    Phase 3 wires to emoji.search_and_update_emoji().
    """
    logger.info('Emoji update triggered')
    # Phase 3 wires to emoji.search_and_update_emoji()
    return '', 200
