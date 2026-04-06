"""Tests for places_client and find_suggestions endpoint."""
import json
from datetime import date
from unittest.mock import patch, MagicMock


class TestPlacesClient:
    """Tests for lunchbot.client.places_client."""

    @patch('lunchbot.client.places_client.session')
    def test_find_suggestion_params(self, mock_session, app):
        """find_suggestion sends correct params to Google Places API."""
        with app.app_context():
            app.config['GOOGLE_PLACES_API_KEY'] = 'test-api-key'
            mock_response = MagicMock()
            mock_response.json.return_value = {'results': []}
            mock_session.get.return_value = mock_response

            from lunchbot.client.places_client import find_suggestion
            result = find_suggestion('pizza', '59.3419,18.0645')

            mock_session.get.assert_called_once()
            call_args = mock_session.get.call_args
            assert 'nearbysearch/json' in call_args[0][0]
            params = call_args[1]['params']
            assert params['keyword'] == 'pizza'
            assert params['location'] == '59.3419,18.0645'
            assert params['radius'] == 700
            assert params['type'] == 'restaurant'
            assert params['key'] == 'test-api-key'
            assert result == {'results': []}

    @patch('lunchbot.client.places_client.session')
    def test_get_details_params(self, mock_session, app):
        """get_details sends correct placeid param."""
        with app.app_context():
            app.config['GOOGLE_PLACES_API_KEY'] = 'test-api-key'
            mock_response = MagicMock()
            mock_response.json.return_value = {'result': {'name': 'Test'}}
            mock_session.get.return_value = mock_response

            from lunchbot.client.places_client import get_details
            result = get_details('ChIJtest123')

            call_args = mock_session.get.call_args
            assert 'details/json' in call_args[0][0]
            params = call_args[1]['params']
            assert params['placeid'] == 'ChIJtest123'
            assert params['key'] == 'test-api-key'
            assert result == {'result': {'name': 'Test'}}


class TestFindSuggestionsEndpoint:
    """Tests for POST /find_suggestions."""

    @patch('lunchbot.blueprints.slack_actions.get_workspace')
    @patch('lunchbot.blueprints.slack_actions.db_client')
    @patch('lunchbot.blueprints.slack_actions.places_client')
    def test_find_suggestions_returns_options(self, mock_places, mock_db, mock_get_ws, app, client):
        """POST /find_suggestions returns formatted Slack options."""
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_get_ws.return_value = {'location': '59.3419,18.0645'}
        mock_places.find_suggestion.return_value = {
            'results': [
                {
                    'place_id': 'ChIJ_pizza1',
                    'name': 'Pizza Place',
                    'rating': 4.2,
                    'opening_hours': {'open_now': True},
                },
            ]
        }
        mock_db.save_restaurants.return_value = [1]

        payload = json.dumps({'value': 'pizza', 'team': {'id': 'T123'}})
        response = client.post('/find_suggestions', data={'payload': payload})

        assert response.status_code == 200
        data = response.get_json()
        assert 'options' in data
        assert len(data['options']) == 1
        option = data['options'][0]
        assert option['value'] == 'ChIJ_pizza1'
        assert 'Pizza Place' in option['text']['text']
        assert 'open' in option['text']['text']
        assert '4.2' in option['text']['text']

    @patch('lunchbot.blueprints.slack_actions.get_workspace')
    @patch('lunchbot.blueprints.slack_actions.db_client')
    @patch('lunchbot.blueprints.slack_actions.places_client')
    def test_find_suggestions_closed_restaurant(self, mock_places, mock_db, mock_get_ws, app, client):
        """Closed restaurant shows 'closed' in option text."""
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_get_ws.return_value = {'location': '59.3419,18.0645'}
        mock_places.find_suggestion.return_value = {
            'results': [
                {
                    'place_id': 'ChIJ_sushi1',
                    'name': 'Sushi Bar',
                    'rating': 3.8,
                    'opening_hours': {'open_now': False},
                },
            ]
        }
        mock_db.save_restaurants.return_value = [1]

        payload = json.dumps({'value': 'sushi', 'team': {'id': 'T123'}})
        response = client.post('/find_suggestions', data={'payload': payload})

        data = response.get_json()
        assert 'closed' in data['options'][0]['text']['text']


class TestSuggestFunction:
    """Tests for suggest() called from external_select action."""

    @patch('lunchbot.blueprints.slack_actions.db_client')
    @patch('lunchbot.blueprints.slack_actions.places_client')
    def test_suggest_creates_poll_option(self, mock_places, mock_db, app, client):
        """External select action calls suggest which upserts poll option."""
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_db.get_restaurant_by_place_id.return_value = {
            'id': 5, 'place_id': 'ChIJ_abc', 'name': 'Test', 'url': 'https://example.com',
        }
        mock_db.upsert_suggestion.return_value = 1

        payload = {
            'type': 'block_actions',
            'team': {'id': 'T123'},
            'actions': [{
                'type': 'external_select',
                'selected_option': {'value': 'ChIJ_abc'},
            }],
        }
        response = client.post('/action', data={
            'payload': json.dumps(payload)
        })

        assert response.status_code == 200
        mock_db.get_restaurant_by_place_id.assert_called_once_with('ChIJ_abc')
        mock_db.upsert_suggestion.assert_called_once_with(date.today(), 5)

    @patch('lunchbot.blueprints.slack_actions.db_client')
    @patch('lunchbot.blueprints.slack_actions.places_client')
    def test_suggest_fetches_details_when_no_url(self, mock_places, mock_db, app, client):
        """suggest() fetches details and updates URL when restaurant has no url."""
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_db.get_restaurant_by_place_id.return_value = {
            'id': 5, 'place_id': 'ChIJ_abc', 'name': 'Test', 'url': None,
        }
        mock_places.get_details.return_value = {
            'result': {'url': 'https://maps.google.com/abc', 'website': 'https://test.com'}
        }
        mock_db.update_restaurant_url.return_value = {}
        mock_db.upsert_suggestion.return_value = 1

        payload = {
            'type': 'block_actions',
            'team': {'id': 'T123'},
            'actions': [{
                'type': 'external_select',
                'selected_option': {'value': 'ChIJ_abc'},
            }],
        }
        response = client.post('/action', data={
            'payload': json.dumps(payload)
        })

        assert response.status_code == 200
        mock_places.get_details.assert_called_once_with('ChIJ_abc')
        mock_db.update_restaurant_url.assert_called_once_with(
            'ChIJ_abc', 'https://maps.google.com/abc', 'https://test.com'
        )
