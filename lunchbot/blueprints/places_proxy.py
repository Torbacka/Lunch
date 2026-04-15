"""Public proxy for Google Places Autocomplete + Details.

Used by the /slack/setup install form so the browser never sees the
Places API key. All requests are proxied through places_client, which
reads the key from Flask config server-side. Only the two whitelisted
Google Places endpoints (autocomplete, details) are reachable — there
is no generic URL pass-through, so there is no SSRF surface.

Trust boundaries (Phase 07.1 threat model):
- T-07.1-01: API key lives only in places_client / Flask config; never
  returned in a proxy response.
- T-07.1-02: User input flows only into `input`/`placeid` query params
  of hardcoded Google Places URLs.
- T-07.1-04: Only whitelisted result fields are returned.
"""
import structlog
from flask import Blueprint, jsonify, request

from lunchbot.client import places_client

logger = structlog.get_logger(__name__)

bp = Blueprint('places_proxy', __name__, url_prefix='/places')


@bp.route('/autocomplete', methods=['GET'])
def autocomplete():
    """Proxy Google Places Autocomplete. Returns normalized predictions."""
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'error': 'q required'}), 400
    session_token = request.args.get('session_token') or places_client.new_session_token()
    data = places_client.autocomplete(q, session_token=session_token)
    predictions = [
        {
            'place_id': p.get('place_id'),
            'description': p.get('description'),
            'main_text': (p.get('structured_formatting') or {}).get('main_text', ''),
            'secondary_text': (p.get('structured_formatting') or {}).get('secondary_text', ''),
        }
        for p in (data.get('predictions') or [])
    ]
    return jsonify({'predictions': predictions, 'session_token': session_token})


@bp.route('/details', methods=['GET'])
def details():
    """Proxy Google Places Details. Returns whitelisted fields only."""
    place_id = (request.args.get('place_id') or '').strip()
    if not place_id:
        return jsonify({'error': 'place_id required'}), 400
    session_token = request.args.get('session_token')
    data = places_client.get_place_details(place_id, session_token=session_token)
    result = data.get('result') or {}
    loc = (result.get('geometry') or {}).get('location') or {}
    if not result.get('place_id') or 'lat' not in loc or 'lng' not in loc:
        logger.warning('places_proxy_details_incomplete', place_id=place_id)
        return jsonify({'error': 'place not found'}), 404
    return jsonify({
        'place_id': result['place_id'],
        'name': result.get('name', ''),
        'formatted_address': result.get('formatted_address', ''),
        'lat': loc['lat'],
        'lng': loc['lng'],
    })
