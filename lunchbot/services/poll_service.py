"""Poll construction service.

Builds Slack Block Kit poll messages from PostgreSQL poll options
and posts them via the per-workspace Slack client.
"""
import structlog
from datetime import date

from flask import current_app

from lunchbot.client import db_client
from lunchbot.client import slack_client
from lunchbot.client.workspace_client import get_workspace_settings
from lunchbot.services.recommendation_service import ensure_poll_options

logger = structlog.get_logger(__name__)


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

        # URL context block — prefer website (restaurant page), fall back to Google Maps url
        link = option.get('website') or option.get('url') or ''
        if link:
            blocks.append({
                'type': 'context',
                'elements': [{
                    'type': 'mrkdwn',
                    'text': f'<{link}|More info>'
                }]
            })

        # Divider
        blocks.append({'type': 'divider'})

    return blocks


def push_poll(channel, team_id, trigger_source='manual'):
    """Build and post today's lunch poll to a Slack channel.

    Fetches today's poll options from the database, constructs Block Kit
    blocks, and posts them via the Slack API.

    Args:
        channel: Slack channel ID or name to post to
        team_id: Slack team ID for workspace token resolution
        trigger_source: Who triggered the poll ('manual' or 'scheduled')

    Returns:
        Slack API response dict
    """
    logger.info('poll_building', channel=channel, team_id=team_id, trigger_source=trigger_source)
    ensure_poll_options(poll_date=date.today())
    options = db_client.get_votes(date.today())
    logger.info('poll_posting', channel=channel, team_id=team_id, restaurant_count=len(options), trigger_source=trigger_source)
    blocks = build_poll_blocks(options)
    result = slack_client.post_message(channel, blocks, team_id)
    try:
        current_app.extensions['prom_polls_posted'].labels(workspace_id=team_id).inc()
    except (KeyError, RuntimeError):
        pass  # metrics not initialized or outside app context
    return result


def build_poll_message(channel, team_id, trigger_source='manual'):
    """Alias for push_poll. Used by some blueprints."""
    return push_poll(channel, team_id, trigger_source=trigger_source)


def poll_channel_for(team_id):
    """Get the poll channel for a workspace. DB value overrides env var (per D-05).

    Args:
        team_id: Slack team ID for workspace lookup

    Returns:
        Channel string from workspace DB row, or config fallback, or empty string
    """
    settings = get_workspace_settings(team_id)
    if settings and settings.get('poll_channel'):
        return settings['poll_channel']
    return current_app.config.get('SLACK_POLL_CHANNEL', '')
