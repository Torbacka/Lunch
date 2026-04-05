"""Vote handling service.

Parses Slack block_actions payload, toggles DB vote, rebuilds Block Kit
blocks from fresh DB data, and updates the Slack message.

Threat mitigations:
  T-03-07: int() cast on poll_option_id; ValueError caught at blueprint level
  T-03-11: Blocks rebuilt from DB data, not from Slack payload blocks
"""
import logging
from datetime import date

from lunchbot.client import db_client
from lunchbot.client import slack_client
from lunchbot.services import poll_service

logger = logging.getLogger(__name__)

# Module-level cache for user profile avatars (T-03-09: non-sensitive data)
profile_cache = {}


def get_voter_image(user_id, team_id):
    """Get cached voter avatar and display name.

    Fetches from Slack API on first call, caches for subsequent calls.
    """
    if user_id in profile_cache:
        return profile_cache[user_id]

    profile = slack_client.get_user_profile(user_id, team_id)
    result = {
        'url': profile.get('image_24', ''),
        'name': profile.get('display_name') or profile.get('real_name', ''),
    }
    profile_cache[user_id] = result
    return result


def build_voter_elements(votes, team_id):
    """Build Slack Block Kit context elements for voter avatars and count.

    Returns list of elements: one image per voter + a text count element.
    """
    elements = []

    for user_id in votes:
        img = get_voter_image(user_id, team_id)
        if img['url']:
            elements.append({
                'type': 'image',
                'image_url': img['url'],
                'alt_text': img['name'],
            })

    # Vote count text
    if votes:
        count = len(votes)
        vote_word = 'vote' if count == 1 else 'votes'
        elements.append({
            'type': 'plain_text',
            'emoji': True,
            'text': f'{count} {vote_word}',
        })
    else:
        elements.append({
            'type': 'plain_text',
            'emoji': True,
            'text': 'No votes',
        })

    return elements


def vote(payload):
    """Handle a vote action from Slack.

    Parses the block_actions payload, toggles the vote in the database,
    fetches fresh poll data, enriches with voter elements, rebuilds
    Block Kit blocks, and updates the Slack message.
    """
    poll_option_id = int(payload['actions'][0]['value'])
    user_id = payload['user']['id']
    channel = payload['channel']['id']
    ts = payload['message']['ts']
    team_id = payload['team']['id']

    # Toggle vote in database
    result = db_client.toggle_vote(poll_option_id, user_id)
    logger.info('Vote %s: option=%s user=%s', result, poll_option_id, user_id)

    # Fetch fresh data from DB (T-03-11: never use payload blocks)
    options = db_client.get_votes(date.today())

    # Enrich options with voter avatar elements
    for option in options:
        option['voter_elements'] = build_voter_elements(
            option.get('votes', []), team_id
        )

    # Rebuild blocks from fresh DB data
    blocks = poll_service.build_poll_blocks(options)

    # Update the Slack message
    slack_client.update_message(channel, ts, blocks, team_id)
