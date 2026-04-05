"""Google Places API client.

Replaces service/client/places_client.py with Flask config-driven key access.
T-03-12: API key read from config only, never logged.
"""
import logging

import requests
from flask import current_app

logger = logging.getLogger(__name__)

session = requests.Session()
PLACES_BASE = "https://maps.googleapis.com/maps/api/place/"


def find_suggestion(search_string):
    """Search for nearby restaurants matching search_string.

    Returns full Google Places API JSON response dict with 'results' list.
    """
    key = current_app.config['GOOGLE_PLACES_API_KEY']
    params = {
        'location': '59.3419128,18.0644956',
        'radius': 600,
        'keyword': search_string,
        'type': 'restaurant',
        'key': key,
    }
    response = session.get(PLACES_BASE + 'nearbysearch/json', params=params)
    return response.json()


def get_details(place_id):
    """Get detailed information for a specific place.

    Returns full Google Places details response dict with 'result' key.
    """
    key = current_app.config['GOOGLE_PLACES_API_KEY']
    params = {
        'placeid': place_id,
        'key': key,
    }
    response = session.get(PLACES_BASE + 'details/json', params=params)
    return response.json()
