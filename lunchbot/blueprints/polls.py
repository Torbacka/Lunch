"""Poll management endpoints.

Handles: /slack/command (slash command), /lunch_message (scheduler trigger),
         /suggestion_message (send suggestion), /emoji (update emoji tags).
"""
import logging

from flask import Blueprint, jsonify, request, current_app

from lunchbot.services import poll_service, emoji_service

logger = logging.getLogger(__name__)

bp = Blueprint('polls', __name__)

HELP_TEXT = (
    "LunchBot commands:\n"
    "\u2022 `/lunch` \u2014 post today's restaurant poll\n"
    "\u2022 `/lunch help` \u2014 show this help message"
)


@bp.route('/slack/command', methods=['POST'])
def slash_command():
    """Handle /lunch slash command from Slack.

    Accepts application/x-www-form-urlencoded body from Slack.
    Routes to help text or poll trigger based on text parameter.
    """
    team_id = request.form.get('team_id', '')
    channel = request.form.get('channel_id', '')
    text = request.form.get('text', '').strip().lower()

    if text == 'help':
        return jsonify({'response_type': 'ephemeral', 'text': HELP_TEXT}), 200

    # Default: trigger poll (empty text, 'start', or any other text)
    try:
        poll_service.push_poll(channel, team_id)
    except ValueError:
        return jsonify({
            'response_type': 'ephemeral',
            'text': 'LunchBot is not configured for this workspace. Install at /slack/install'
        }), 200

    return '', 200


@bp.route('/lunch_message')
def lunch_message():
    """Trigger lunch poll message to Slack channel.
    Used by scheduler/manual HTTP GET trigger.
    """
    channel = request.args.get('channel', current_app.config.get('SLACK_POLL_CHANNEL', ''))
    team_id = request.args.get('team_id', '')
    logger.info('Lunch message triggered for channel=%s team=%s', channel, team_id)
    try:
        poll_service.push_poll(channel, team_id)
    except ValueError as e:
        logger.warning('Push poll failed: %s', e)
        return str(e), 400
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
    emoji_service.search_and_update_emoji()
    return '', 200
