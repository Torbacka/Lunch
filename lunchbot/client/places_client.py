"""Google Places API client.

Replaces service/client/places_client.py with Flask config-driven key access.
T-03-12: API key read from config only, never logged.
"""
import logging
import uuid

import requests
from flask import current_app

logger = logging.getLogger(__name__)

session = requests.Session()
PLACES_BASE = "https://maps.googleapis.com/maps/api/place/"


def find_suggestion(search_string, location):
    """Search for nearby restaurants matching search_string.

    Args:
        search_string: keyword to search for (e.g. 'pizza')
        location: 'lat,lng' string for the search center (e.g. '59.3419,18.0645')

    Returns full Google Places API JSON response dict with 'results' list.
    """
    key = current_app.config['GOOGLE_PLACES_API_KEY']
    params = {
        'location': location,
        'radius': 700,
        'keyword': search_string,
        'type': 'restaurant',
        'key': key,
    }
    response = session.get(PLACES_BASE + 'nearbysearch/json', params=params)
    data = response.json()
    _check_status(data, 'nearbysearch')
    return data


def find_restaurants_nearby(location, radius=700):
    """Fetch all restaurants within radius metres of location.

    No keyword filter — returns everything Google Places classifies as a
    restaurant. Used for initial workspace seeding.

    Args:
        location: 'lat,lng' string (e.g. '59.3419,18.0645')
        radius: search radius in metres (default 700)

    Returns full Google Places API JSON response dict with 'results' list.
    """
    key = current_app.config['GOOGLE_PLACES_API_KEY']
    params = {
        'location': location,
        'radius': radius,
        'type': 'restaurant',
        'key': key,
    }
    response = session.get(PLACES_BASE + 'nearbysearch/json', params=params)
    data = response.json()
    _check_status(data, 'nearbysearch')
    return data


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
    data = response.json()
    _check_status(data, 'details')
    return data


def new_session_token():
    """Return a fresh Places Autocomplete session token (uuid4 hex).

    Bundle one Autocomplete sequence + one Details call under the same
    token so Google bills a single session instead of per-keystroke
    autocomplete pricing.
    """
    return uuid.uuid4().hex


def autocomplete(query, session_token, types='establishment'):
    """Google Places Autocomplete query (used by the install-form proxy).

    Args:
        query: user-typed string (e.g. 'Spotify HQ')
        session_token: opaque token bundling this query with a later
            get_place_details call — required for session-based billing.
        types: Places types filter; default 'establishment' for office
            name search.

    Returns the full Google Places API JSON dict with 'predictions' list.
    API key is read server-side only and never returned or logged.
    """
    key = current_app.config['GOOGLE_PLACES_API_KEY']
    params = {
        'input': query,
        'sessiontoken': session_token,
        'types': types,
        'key': key,
    }
    response = session.get(PLACES_BASE + 'autocomplete/json', params=params)
    data = response.json()
    _check_status(data, 'autocomplete')
    return data


def get_place_details(place_id, session_token=None):
    """Fetch minimal Place Details for an office: name, address, lat/lng.

    Uses a restricted field mask (Basic tier only) to minimize billing.
    If session_token is provided the call is charged as part of the
    same Autocomplete session (Session Token pricing).
    """
    key = current_app.config['GOOGLE_PLACES_API_KEY']
    params = {
        'placeid': place_id,
        'fields': 'place_id,name,formatted_address,geometry/location',
        'key': key,
    }
    if session_token:
        params['sessiontoken'] = session_token
    response = session.get(PLACES_BASE + 'details/json', params=params)
    data = response.json()
    _check_status(data, 'details')
    return data


def _check_status(data, endpoint):
    """Log warning if Google Places API returned a non-OK status."""
    status = data.get('status', '')
    if status != 'OK' and status != 'ZERO_RESULTS':
        error_msg = data.get('error_message', 'no error message')
        logger.error('Google Places %s failed: status=%s error=%s',
                     endpoint, status, error_msg)
