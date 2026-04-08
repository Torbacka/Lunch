"""Tests for cuisine classification from Google Places types."""
from lunchbot.services.cuisine_map import classify_cuisine


class TestClassifyCuisine:

    def test_bakery_type(self):
        assert classify_cuisine(['restaurant', 'bakery', 'food']) == 'Bakery'

    def test_cafe_type(self):
        assert classify_cuisine(['cafe', 'food']) == 'Cafe'

    def test_bar_type(self):
        assert classify_cuisine(['bar', 'restaurant']) == 'Bar'

    def test_japanese_from_name(self):
        assert classify_cuisine(['restaurant', 'food'], 'Sushi Yama') == 'Japanese'

    def test_ramen_from_name(self):
        assert classify_cuisine(['restaurant'], 'Ramen House') == 'Japanese'

    def test_italian_from_name(self):
        assert classify_cuisine(['restaurant'], 'Pasta Palace') == 'Italian'

    def test_pizza_from_name(self):
        assert classify_cuisine(['restaurant'], 'Pizza Hut') == 'Pizza'

    def test_burger_from_name(self):
        assert classify_cuisine(['restaurant'], 'Burger King') == 'Burgers'

    def test_indian_from_name(self):
        assert classify_cuisine(['restaurant'], 'Curry House') == 'Indian'

    def test_thai_from_name(self):
        assert classify_cuisine(['restaurant'], 'Thai Wok') == 'Thai'

    def test_mexican_from_name(self):
        assert classify_cuisine(['restaurant'], 'Taco Bell') == 'Mexican'

    def test_kebab_from_name(self):
        assert classify_cuisine(['restaurant'], 'Kebab House') == 'Kebab'

    def test_no_match_returns_none(self):
        assert classify_cuisine(['restaurant', 'food'], 'The Place') is None

    def test_empty_types_and_name(self):
        assert classify_cuisine([], '') is None

    def test_none_types(self):
        assert classify_cuisine(None) is None

    def test_name_keyword_case_insensitive(self):
        assert classify_cuisine(['restaurant'], 'SUSHI PALACE') == 'Japanese'

    def test_type_priority_over_name(self):
        """Specific type (bakery) should win over name keyword (sushi)."""
        assert classify_cuisine(['bakery', 'restaurant'], 'Sushi Bakery') == 'Bakery'
