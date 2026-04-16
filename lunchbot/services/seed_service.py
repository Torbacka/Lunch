"""Shared office restaurant seeding helper.

Used by both the install flow (setup.py) and the add-office Slack modal
(slack_actions.py) to populate workspace_locations with a tagged candidate pool.
"""
from flask import g

from lunchbot.services import emoji_service


def _seed_office_restaurants(app, team_id, location_id, lat_lng):
    """Seed restaurants for a newly created workspace_locations row.

    Args:
        app: Flask app (for app_context in background thread callers)
        team_id: workspaces.team_id (tenant)
        location_id: workspace_locations.id (must exist)
        lat_lng: dict with 'lat' and 'lng' or 'lat,lng' string (Places search origin)
    """
    with app.app_context():
        g.workspace_id = team_id
        emoji_service.search_and_update_emoji(lat_lng, location_id, team_id)
