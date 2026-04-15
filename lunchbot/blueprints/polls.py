"""Poll management endpoints.

Handles: /slack/command (slash command), /lunch_message (scheduler trigger),
         /suggestion_message (send suggestion), /seed (seed restaurants).
"""
import logging

from flask import Blueprint, jsonify, request, current_app

from lunchbot.services import poll_service, emoji_service
from lunchbot.client.workspace_client import (
    resolve_location_for_channel, list_workspace_locations,
)

logger = logging.getLogger(__name__)

bp = Blueprint('polls', __name__)

# Action IDs for the channel-location first-use prompt (dispatched in slack_actions.py)
CHANNEL_LOC_USE_DEFAULT = 'channel_loc_use_default'
CHANNEL_LOC_PICK = 'channel_loc_pick'
CHANNEL_LOC_ADD_OFFICE = 'channel_loc_add_office'

HELP_TEXT = (
    "LunchBot commands:\n"
    "\u2022 `/lunch` \u2014 post today's restaurant poll\n"
    "\u2022 `/lunch close` \u2014 close the poll and announce the winner\n"
    "\u2022 `/lunch help` \u2014 show this help message"
)


def _build_channel_location_prompt(team_id, channel_id):
    """Build the ephemeral Block Kit payload that asks the user to pick or
    create an office location for an unbound channel.

    Phase 07.1 D-05/D-06/D-09: always prompts, even for single-office
    workspaces; always exposes 'Add a new office'; zero-office workspaces
    see only the Add button.
    """
    locations = list_workspace_locations(team_id) or []

    if locations:
        text = (
            ':round_pushpin: Pick an office for this channel, or add a new one. '
            "We'll remember your choice for next time."
        )
    else:
        text = (
            ':round_pushpin: This workspace has no offices yet. '
            'Add one to start posting lunch polls in this channel.'
        )

    blocks = [{
        'type': 'section',
        'text': {'type': 'mrkdwn', 'text': text},
    }]

    action_elements = []
    if locations:
        action_elements.append({
            'type': 'static_select',
            'action_id': CHANNEL_LOC_PICK,
            'placeholder': {'type': 'plain_text', 'text': 'Pick an office'},
            'options': [
                {
                    'text': {'type': 'plain_text', 'text': loc['name']},
                    'value': str(loc['id']),
                }
                for loc in locations
            ],
        })
    action_elements.append({
        'type': 'button',
        'action_id': CHANNEL_LOC_ADD_OFFICE,
        'text': {'type': 'plain_text', 'text': 'Add a new office', 'emoji': True},
        'value': channel_id,
    })

    blocks.append({'type': 'actions', 'elements': action_elements})

    return {
        'response_type': 'ephemeral',
        'blocks': blocks,
    }


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

    if text == 'close':
        try:
            poll_service.close_poll(channel, team_id)
        except ValueError:
            return jsonify({
                'response_type': 'ephemeral',
                'text': 'LunchBot is not configured for this workspace. Install at /slack/install'
            }), 200
        return '', 200

    # Default: trigger poll (empty text, 'start', or any other text).
    # First, resolve the office location for this channel. If unbound and the
    # workspace has multiple locations (or zero), prompt the user to pick one.
    location = resolve_location_for_channel(team_id, channel)
    if location is None:
        logger.info('channel_location_prompt team=%s channel=%s', team_id, channel)
        return jsonify(_build_channel_location_prompt(team_id, channel)), 200

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
    Used by scheduler/manual HTTP GET trigger. The scheduler cannot prompt a
    human, so an unbound channel must fail loudly.
    """
    channel = request.args.get('channel', current_app.config.get('SLACK_POLL_CHANNEL', ''))
    team_id = request.args.get('team_id', '')
    logger.info('Lunch message triggered for channel=%s team=%s', channel, team_id)

    location = resolve_location_for_channel(team_id, channel) if team_id and channel else None
    if location is None:
        logger.warning('lunch_message channel not bound to a location team=%s channel=%s', team_id, channel)
        return 'channel not bound to a location', 400

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


@bp.route('/seed', methods=['GET'])
def seed():
    """Seed restaurants and update emoji tags for a channel's office.

    Requires team_id AND channel query params; resolves the effective office
    location via the per-channel binding (migration 007). Seeding is now
    channel-scoped so multi-location workspaces can seed each office
    independently.
    """
    team_id = request.args.get('team_id', '')
    channel = request.args.get('channel', '')
    if not team_id or not channel:
        return 'team_id and channel query params required', 400

    location_row = resolve_location_for_channel(team_id, channel)
    location = location_row.get('lat_lng') if location_row else None
    if not location:
        logger.warning('Seed skipped: no location bound for team_id=%s channel=%s', team_id, channel)
        return 'no location bound for channel', 400

    logger.info('Restaurant seed triggered for team_id=%s channel=%s', team_id, channel)
    emoji_service.search_and_update_emoji(location)
    return '', 200
