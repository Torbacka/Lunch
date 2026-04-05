"""Tests for emoji_service and GET /emoji endpoint."""
import json
from unittest.mock import patch, MagicMock, call


class TestEmojiService:
    """Tests for lunchbot.services.emoji_service."""

    @patch('lunchbot.services.emoji_service.db_client')
    @patch('lunchbot.services.emoji_service.places_client')
    def test_search_and_update_emoji(self, mock_places, mock_db, app):
        """search_and_update_emoji loads food_emoji.json and calls add_emoji for each category."""
        with app.app_context():
            mock_places.find_suggestion.return_value = {
                'results': [
                    {'place_id': 'ChIJ_burger1'},
                    {'place_id': 'ChIJ_burger2'},
                ]
            }
            mock_db.add_emoji.return_value = 2

            from lunchbot.services.emoji_service import search_and_update_emoji
            search_and_update_emoji()

            # Should have been called for every search_query in food_emoji.json
            assert mock_places.find_suggestion.call_count > 0
            # add_emoji should be called for each emoji category
            assert mock_db.add_emoji.call_count > 0

    @patch('lunchbot.services.emoji_service.db_client')
    @patch('lunchbot.services.emoji_service.places_client')
    def test_emoji_collects_place_ids(self, mock_places, mock_db, app):
        """add_emoji receives place_ids extracted from Places API response."""
        with app.app_context():
            mock_places.find_suggestion.return_value = {
                'results': [
                    {'place_id': 'ChIJ_pizza1'},
                    {'place_id': 'ChIJ_pizza2'},
                ]
            }
            mock_db.add_emoji.return_value = 2

            from lunchbot.services.emoji_service import search_and_update_emoji
            search_and_update_emoji()

            # Find the call for 'pizza' emoji (search_query: ["pizza"])
            pizza_calls = [c for c in mock_db.add_emoji.call_args_list
                           if c[0][1] == 'pizza']
            assert len(pizza_calls) == 1
            place_ids = pizza_calls[0][0][0]
            assert 'ChIJ_pizza1' in place_ids
            assert 'ChIJ_pizza2' in place_ids

    @patch('lunchbot.services.emoji_service.db_client')
    @patch('lunchbot.services.emoji_service.places_client')
    def test_emoji_multiple_search_queries(self, mock_places, mock_db, app):
        """Emoji with multiple search_queries accumulates results from all searches."""
        with app.app_context():
            # Return different results for different searches
            def fake_find(search_string):
                if search_string == 'indian':
                    return {'results': [{'place_id': 'ChIJ_indian1'}]}
                elif search_string == 'curry':
                    return {'results': [{'place_id': 'ChIJ_curry1'}]}
                return {'results': []}

            mock_places.find_suggestion.side_effect = fake_find
            mock_db.add_emoji.return_value = 1

            from lunchbot.services.emoji_service import search_and_update_emoji
            search_and_update_emoji()

            # curry_rice has search_queries: ["indian", "curry"]
            curry_calls = [c for c in mock_db.add_emoji.call_args_list
                           if c[0][1] == 'curry_rice']
            assert len(curry_calls) == 1
            place_ids = curry_calls[0][0][0]
            assert 'ChIJ_indian1' in place_ids
            assert 'ChIJ_curry1' in place_ids


class TestEmojiEndpoint:
    """Tests for GET /emoji endpoint."""

    @patch('lunchbot.blueprints.polls.emoji_service')
    def test_emoji_endpoint_returns_200(self, mock_emoji, app, client):
        """GET /emoji calls search_and_update_emoji and returns 200."""
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_emoji.search_and_update_emoji.return_value = None

        response = client.get('/emoji')

        assert response.status_code == 200
        mock_emoji.search_and_update_emoji.assert_called_once()
