"""Walking distance estimation using Haversine formula.

Calculates straight-line distance and converts to approximate walking
minutes using an average walking speed of 5 km/h with a 1.3x detour
factor (streets aren't straight lines).
"""
import math

_EARTH_RADIUS_KM = 6371.0
_WALK_SPEED_KMH = 5.0
_DETOUR_FACTOR = 1.3


def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance between two points in kilometres.

    Args:
        lat1, lon1: origin coordinates (degrees)
        lat2, lon2: destination coordinates (degrees)

    Returns:
        Distance in kilometres.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def estimate_walking_minutes(origin_lat, origin_lon, dest_lat, dest_lon):
    """Estimate walking time in minutes between two coordinates.

    Uses Haversine distance with a 1.3x detour factor and 5 km/h walk speed.

    Args:
        origin_lat, origin_lon: workspace/office location
        dest_lat, dest_lon: restaurant location

    Returns:
        Walking minutes as an integer, or None if coordinates are missing.
    """
    if any(v is None for v in [origin_lat, origin_lon, dest_lat, dest_lon]):
        return None
    km = haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
    walking_km = km * _DETOUR_FACTOR
    minutes = (walking_km / _WALK_SPEED_KMH) * 60
    return round(minutes)
