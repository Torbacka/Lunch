"""Tests for emoji_service and GET /seed endpoint."""
from unittest.mock import patch, MagicMock


FAKE_RESULTS = [
    {'place_id': 'ChIJ_place1', 'name': 'Place 1'},
    {'place_id': 'ChIJ_place2', 'name': 'Place 2'},
]

LOCATION = '59.3419,18.0645'


class TestEmojiService:
    """Tests for lunchbot.services.emoji_service."""

    @patch('lunchbot.services.emoji_service.db_client')
    @patch('lunchbot.services.emoji_service.places_client')
    def test_search_and_update_emoji(self, mock_places, mock_db, app):
        """search_and_update_emoji seeds restaurants and tags with emoji."""
        with app.app_context():
            mock_places.find_restaurants_nearby.return_value = {'results': FAKE_RESULTS}
            mock_places.get_details.return_value = {'result': {}}
            mock_places.find_suggestion.return_value = {
                'results': [{'place_id': 'ChIJ_burger1'}, {'place_id': 'ChIJ_burger2'}]
            }
            mock_db.add_emoji.return_value = 2
            mock_db.save_restaurants.return_value = [1, 2]

            from lunchbot.services.emoji_service import search_and_update_emoji
            search_and_update_emoji(LOCATION)

            mock_places.find_restaurants_nearby.assert_called_once_with(LOCATION)
            mock_db.save_restaurants.assert_called_once()
            assert mock_places.find_suggestion.call_count > 0
            assert mock_db.add_emoji.call_count > 0

    @patch('lunchbot.services.emoji_service.db_client')
    @patch('lunchbot.services.emoji_service.places_client')
    def test_emoji_collects_place_ids(self, mock_places, mock_db, app):
        """add_emoji receives place_ids extracted from Places API response."""
        with app.app_context():
            mock_places.find_restaurants_nearby.return_value = {'results': FAKE_RESULTS}
            mock_places.get_details.return_value = {'result': {}}
            mock_places.find_suggestion.return_value = {
                'results': [{'place_id': 'ChIJ_sushi1'}, {'place_id': 'ChIJ_sushi2'}]
            }
            mock_db.add_emoji.return_value = 2
            mock_db.save_restaurants.return_value = [1, 2]

            from lunchbot.services.emoji_service import search_and_update_emoji
            search_and_update_emoji(LOCATION)

            sushi_calls = [c for c in mock_db.add_emoji.call_args_list
                           if c[0][1] == 'sushi']
            assert len(sushi_calls) == 1
            place_ids = sushi_calls[0][0][0]
            assert 'ChIJ_sushi1' in place_ids
            assert 'ChIJ_sushi2' in place_ids

    @patch('lunchbot.services.emoji_service.db_client')
    @patch('lunchbot.services.emoji_service.places_client')
    def test_no_restaurants_found(self, mock_places, mock_db, app):
        """search_and_update_emoji returns early if no restaurants found."""
        with app.app_context():
            mock_places.find_restaurants_nearby.return_value = {'results': []}

            from lunchbot.services.emoji_service import search_and_update_emoji
            search_and_update_emoji(LOCATION)

            mock_db.save_restaurants.assert_not_called()
            mock_db.add_emoji.assert_not_called()

    @patch('lunchbot.services.emoji_service.db_client')
    @patch('lunchbot.services.emoji_service.places_client')
    def test_details_fetched_for_urls(self, mock_places, mock_db, app):
        """get_details is called for each restaurant to fetch website/url."""
        with app.app_context():
            mock_places.find_restaurants_nearby.return_value = {'results': FAKE_RESULTS}
            mock_places.get_details.return_value = {
                'result': {'website': 'https://example.com', 'url': 'https://maps.google.com/?cid=123'}
            }
            mock_places.find_suggestion.return_value = {'results': []}
            mock_db.save_restaurants.return_value = [1, 2]

            from lunchbot.services.emoji_service import search_and_update_emoji
            search_and_update_emoji(LOCATION)

            assert mock_places.get_details.call_count == len(FAKE_RESULTS)
            assert mock_db.update_restaurant_urls.call_count == len(FAKE_RESULTS)


class TestSeedEndpoint:
    """Tests for GET /seed endpoint."""

    @patch('lunchbot.blueprints.polls.emoji_service')
    def test_seed_endpoint_returns_200(self, mock_emoji, app, client):
        """GET /seed calls search_and_update_emoji and returns 200."""
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_emoji.search_and_update_emoji.return_value = None

        response = client.get('/seed')

        assert response.status_code == 200
        mock_emoji.search_and_update_emoji.assert_called_once()
