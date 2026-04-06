"""Poll construction service.

Builds Slack Block Kit poll messages from PostgreSQL poll options
and posts them via the per-workspace Slack client.
"""
import logging
from datetime import date

from flask import current_app

from lunchbot.client import db_client
from lunchbot.client import slack_client
from lunchbot.services.recommendation_service import ensure_poll_options

logger = logging.getLogger(__name__)


def build_poll_blocks(options):
    """Build Slack Block Kit blocks for a lunch poll.

    Args:
        options: List of option dicts from db_client.get_votes().
            Each dict has: id, name, rating, emoji, url, votes (list of user_ids).

    Returns:
        List of Block Kit block dicts ready for Slack API.
    """
    blocks = []

    # Header
    blocks.append({
        'type': 'section',
        'text': {
            'type': 'mrkdwn',
            'text': ':fork_and_knife: *Where should we eat today?*'
        }
    })
    blocks.append({'type': 'divider'})

    for option in options:
        emoji = option.get('emoji') or 'knife_fork_plate'

        # Restaurant section with vote button
        blocks.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f':{emoji}: *{option["name"]}* {option.get("rating", "")}:star:'
            },
            'accessory': {
                'type': 'button',
                'text': {
                    'type': 'plain_text',
                    'text': 'vote',
                    'emoji': True
                },
                'value': str(option['id'])
            }
        })

        # Vote count context block (with voter avatars if available)
        voter_elements = option.get('voter_elements')
        if voter_elements:
            blocks.append({
                'type': 'context',
                'elements': voter_elements
            })
        else:
            votes = option.get('votes') or []
            if votes:
                count = len(votes)
                vote_word = 'vote' if count == 1 else 'votes'
                vote_text = f'{count} {vote_word}'
            else:
                vote_text = 'No votes'

            blocks.append({
                'type': 'context',
                'elements': [{
                    'type': 'plain_text',
                    'emoji': True,
                    'text': vote_text
                }]
            })

        # URL context block
        blocks.append({
            'type': 'context',
            'elements': [{
                'type': 'mrkdwn',
                'text': f'For more info: {option.get("url", "")}'
            }]
        })

        # Divider
        blocks.append({'type': 'divider'})

    return blocks


def push_poll(channel, team_id):
    """Build and post today's lunch poll to a Slack channel.

    Fetches today's poll options from the database, constructs Block Kit
    blocks, and posts them via the Slack API.

    Args:
        channel: Slack channel ID or name to post to
        team_id: Slack team ID for workspace token resolution

    Returns:
        Slack API response dict
    """
    ensure_poll_options(poll_date=date.today())
    options = db_client.get_votes(date.today())
    blocks = build_poll_blocks(options)
    return slack_client.post_message(channel, blocks, team_id)


def build_poll_message(channel, team_id):
    """Alias for push_poll. Used by some blueprints."""
    return push_poll(channel, team_id)


def poll_channel_for(team_id):
    """Get the poll channel for a workspace.

    Phase 5 will upgrade this to read from workspace settings in the DB.
    For now, returns the app-wide config value.

    Args:
        team_id: Slack team ID (unused until Phase 5 workspace settings)

    Returns:
        Channel string from config, or empty string if not configured
    """
    return current_app.config.get('SLACK_POLL_CHANNEL', '')
