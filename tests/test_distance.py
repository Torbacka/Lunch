"""Tests for walking distance estimation."""
from lunchbot.services.distance import haversine_km, estimate_walking_minutes


class TestHaversine:

    def test_same_point_is_zero(self):
        assert haversine_km(59.3419, 18.0645, 59.3419, 18.0645) == 0.0

    def test_known_distance_stockholm(self):
        """Stockholm Central to Gamla Stan is roughly 0.7-0.9 km."""
        km = haversine_km(59.3308, 18.0586, 59.3251, 18.0711)
        assert 0.5 < km < 1.5

    def test_symmetry(self):
        d1 = haversine_km(59.34, 18.06, 59.35, 18.07)
        d2 = haversine_km(59.35, 18.07, 59.34, 18.06)
        assert abs(d1 - d2) < 1e-10


class TestWalkingMinutes:

    def test_short_walk(self):
        """500m straight-line should be roughly 5-10 min walk."""
        # Points ~500m apart
        mins = estimate_walking_minutes(59.3419, 18.0645, 59.3464, 18.0645)
        assert 3 <= mins <= 15

    def test_same_location_is_zero(self):
        mins = estimate_walking_minutes(59.3419, 18.0645, 59.3419, 18.0645)
        assert mins == 0

    def test_returns_none_for_missing_coords(self):
        assert estimate_walking_minutes(None, 18.0, 59.3, 18.1) is None
        assert estimate_walking_minutes(59.3, None, 59.3, 18.1) is None
        assert estimate_walking_minutes(59.3, 18.0, None, 18.1) is None
        assert estimate_walking_minutes(59.3, 18.0, 59.3, None) is None

    def test_returns_integer(self):
        mins = estimate_walking_minutes(59.34, 18.06, 59.35, 18.07)
        assert isinstance(mins, int)
