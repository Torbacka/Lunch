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
            Each dict has: id, name, rating, emoji, url, cuisine,
            walking_minutes, pick_type, votes (list of user_ids).

    Returns:
        List of Block Kit block dicts ready for Slack API.
    """
    blocks = []
    all_voter_ids = set()

    # Header block
    blocks.append({
        'type': 'header',
        'text': {
            'type': 'plain_text',
            'text': ':fork_and_knife: Lunch Poll',
            'emoji': True,
        }
    })
    blocks.append({
        'type': 'section',
        'text': {
            'type': 'mrkdwn',
            'text': 'Where should we eat today?'
        }
    })
    blocks.append({'type': 'divider'})

    for option in options:
        votes = option.get('votes') or []
        all_voter_ids.update(votes)

        # Restaurant line with cuisine, distance, pick badge
        line = _restaurant_line(option)
        blocks.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': line,
            },
            'accessory': {
                'type': 'button',
                'text': {
                    'type': 'plain_text',
                    'text': ':ballot_box_with_ballot: Vote',
                    'emoji': True,
                },
                'value': str(option['id']),
                'style': 'primary',
            }
        })

        # Voter avatars + count
        voter_elements = option.get('voter_elements')
        if not voter_elements:
            voter_elements = _fallback_vote_text(votes)
        blocks.append({'type': 'context', 'elements': voter_elements})

        # Link (optional)
        link = option.get('website') or option.get('url') or ''
        if link:
            blocks.append({
                'type': 'context',
                'elements': [{'type': 'mrkdwn', 'text': f'<{link}|:round_pushpin: More info>'}]
            })

        blocks.append({'type': 'divider'})

    # Footer with unique voter count
    unique_count = len(all_voter_ids)
    voter_word = 'voter' if unique_count == 1 else 'voters'
    blocks.append({
        'type': 'context',
        'elements': [{'type': 'mrkdwn', 'text': f':bar_chart: *{unique_count} {voter_word}*'}]
    })

    return blocks


def _restaurant_line(option):
    """Build mrkdwn text: :emoji: *Name* rating · Cuisine  :walking: Xmin  :brain: Smart"""
    emoji = option.get('emoji') or 'fork_and_knife'
    rating = option.get('rating')
    name_part = f':{emoji}: *{option["name"]}*'
    if rating:
        name_part += f' {rating}:star:'
    parts = [name_part]

    if cuisine := option.get('cuisine'):
        parts[0] += f' \u00b7 {cuisine}'

    if (mins := option.get('walking_minutes')) is not None:
        parts.append(f':walking: {mins} min')

    pick_type = option.get('pick_type', 'random')
    badge = ':brain: `Smart`' if pick_type == 'smart' else ':game_die: `Wild Card`'
    parts.append(badge)

    return '  '.join(parts)


def _fallback_vote_text(votes):
    """Fallback context elements when voter_elements aren't pre-built."""
    if votes:
        count = len(votes)
        return [{'type': 'plain_text', 'emoji': True,
                 'text': f'{count} {"vote" if count == 1 else "votes"}'}]
    return [{'type': 'mrkdwn', 'text': '_No votes yet_'}]


def close_poll(channel, team_id):
    """Close today's poll and announce the winner.

    Finds the restaurant with the most votes and posts a trophy
    announcement message to the channel.

    Args:
        channel: Slack channel ID to post the announcement
        team_id: Slack team ID for workspace token resolution

    Returns:
        Slack API response dict, or None if no votes were cast.
    """
    from datetime import date as _date
    winner = db_client.get_poll_winner(_date.today())
    if not winner:
        blocks = [{
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': ':shrug: No votes were cast today. Maybe tomorrow!'
            }
        }]
        return slack_client.post_message(channel, blocks, team_id)

    emoji = winner.get('emoji') or 'fork_and_knife'
    name = winner['name']
    vote_count = winner['vote_count']
    vote_word = 'vote' if vote_count == 1 else 'votes'

    blocks = [
        {
            'type': 'header',
            'text': {
                'type': 'plain_text',
                'text': ':trophy: We have a winner!',
                'emoji': True,
            }
        },
        {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f':{emoji}: *{name}* won with *{vote_count} {vote_word}*!',
            }
        },
    ]

    # Add cuisine and walking info if available
    details = []
    if winner.get('cuisine'):
        details.append(winner['cuisine'])
    if winner.get('walking_minutes') is not None:
        details.append(f':walking: {winner["walking_minutes"]} min walk')
    if details:
        blocks.append({
            'type': 'context',
            'elements': [{'type': 'mrkdwn', 'text': ' \u00b7 '.join(details)}]
        })

    # Add link if available
    link = winner.get('website') or winner.get('url') or ''
    if link:
        blocks.append({
            'type': 'context',
            'elements': [{'type': 'mrkdwn', 'text': f'<{link}|:round_pushpin: Directions>'}]
        })

    logger.info('poll_winner_announced', winner=name, votes=vote_count, team_id=team_id)
    return slack_client.post_message(channel, blocks, team_id)


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
