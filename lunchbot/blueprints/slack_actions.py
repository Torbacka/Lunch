"""Slack interactive action endpoints.

Handles: /action (vote clicks, suggestion select), /find_suggestions (external select search).
"""
import json
import logging
from datetime import date

from flask import Blueprint, request, jsonify

from lunchbot.client import places_client, db_client
from lunchbot.services import vote_service

logger = logging.getLogger(__name__)

bp = Blueprint('slack_actions', __name__)


def suggest(place_id):
    """Add a restaurant as a poll option for today.

    Fetches restaurant from DB by place_id. If url is missing, fetches
    details from Google Places API and updates the restaurant record.
    Then upserts a poll option for today.
    T-03-17: place_id used in parameterized SQL only.
    """
    restaurant = db_client.get_restaurant_by_place_id(place_id)
    if restaurant and not restaurant.get('url'):
        details = places_client.get_details(place_id)
        result = details.get('result', {})
        db_client.update_restaurant_url(
            place_id,
            result.get('url', ''),
            result.get('website', ''),
        )
    if restaurant:
        db_client.upsert_suggestion(date.today(), restaurant['id'])


@bp.route('/action', methods=['POST'])
def action():
    """Handle Slack interactive actions (button clicks, external selects).

    Routes button actions to vote_service for vote toggling.
    Routes external_select actions to suggest() for poll option creation.
    T-03-07: int() cast in vote_service catches malformed poll_option_id.
    """
    payload = json.loads(request.form.get('payload', '{}'))
    logger.info('Received action type: %s', payload.get('type', 'unknown'))

    actions = payload.get('actions', [])
    if actions:
        action_type = actions[0].get('type')
        if action_type == 'button':
            vote_service.vote(payload)
        elif action_type == 'external_select':
            selected = actions[0].get('selected_option', {})
            suggest(selected.get('value', ''))

    return '', 200


@bp.route('/find_suggestions', methods=['POST'])
def find_suggestions():
    """Handle Slack external select search for restaurants.

    Parses payload from form field, searches Google Places API,
    caches results in PostgreSQL, and returns formatted Slack options.
    T-03-13: search string passed as Places API keyword, not SQL.
    T-03-15: Slack signature middleware validates request origin.
    """
    payload = json.loads(request.form.get('payload', '{}'))
    search_value = payload.get('value', '')
    logger.info('Received suggestion search: %s', search_value)

    response = places_client.find_suggestion(search_value)
    db_client.save_restaurants(response)

    options = []
    for result in response.get('results', []):
        opening_hours = result.get('opening_hours', {})
        open_status = 'open' if opening_hours.get('open_now') else 'closed'
        rating = result.get('rating', '')
        name = result.get('name', '')
        text = f"{name} {open_status} {rating}"
        options.append({
            'text': {'type': 'plain_text', 'text': text},
            'value': result['place_id'],
        })

    return jsonify({'options': options})
