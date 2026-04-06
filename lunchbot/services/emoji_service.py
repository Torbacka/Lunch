"""Emoji tagging service.

Migrated from service/emoji.py — uses db_client.add_emoji and places_client
instead of mongo_client and os.environ access.
"""
import json
import logging
import os

from flask import current_app

from flask import g

from lunchbot.client import places_client, db_client

logger = logging.getLogger(__name__)


def search_suggestions(emoji_entry, location):
    """Search Google Places for each search_query in an emoji entry.

    Returns list of result dicts from all search queries combined.
    """
    results = []
    for search in emoji_entry['search_query']:
        logger.info('Searching for %s in nearby searches', search)
        response = places_client.find_suggestion(search, location)
        results.extend(response.get('results', []))
    return results


def update_database(results, emoji_string):
    """Update emoji tag for all restaurants found in results.

    Extracts place_ids from results and calls db_client.add_emoji.
    """
    place_ids = [r['place_id'] for r in results]
    if place_ids:
        count = db_client.add_emoji(place_ids, emoji_string)
        logger.info('Updated %d restaurants with emoji %s', count, emoji_string)


def search_and_update_emoji(location):
    """Load food_emoji.json and update emoji tags for all restaurants.

    For each emoji category, searches Google Places for matching restaurants
    near the given location and updates their emoji field in PostgreSQL.

    Args:
        location: 'lat,lng' string (e.g. '59.3419,18.0645')
    """
    json_path = os.path.join(current_app.root_path, '..', 'resources', 'food_emoji.json')
    with open(json_path) as json_file:
        emojis = json.load(json_file)

    for emoji_entry in emojis:
        results = search_suggestions(emoji_entry, location)
        if results:
            db_client.save_restaurants({'results': results})
            update_database(results, emoji_entry['emoji'])
