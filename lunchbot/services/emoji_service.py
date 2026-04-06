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
        found = response.get('results', [])
        logger.info('Found %d restaurants for query "%s"', len(found), search)
        for r in found:
            logger.debug('  -> %s (place_id=%s)', r.get('name', '?'), r.get('place_id', '?'))
        results.extend(found)
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
    """Seed the restaurant database from Google Places.

    Fetches all restaurants within 700m of location, saves them, then
    applies emoji tags by matching against food_emoji.json search terms.

    Args:
        location: 'lat,lng' string (e.g. '59.3419,18.0645')
    """
    response = places_client.find_restaurants_nearby(location)
    results = response.get('results', [])
    if not results:
        logger.warning('No restaurants found near %s', location)
        return

    db_client.save_restaurants({'results': results})
    logger.info('Saved %d restaurants near %s', len(results), location)
