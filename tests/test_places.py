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

    @patch('lunchbot.blueprints.slack_actions.resolve_location_for_channel')
    @patch('lunchbot.blueprints.slack_actions.db_client')
    @patch('lunchbot.blueprints.slack_actions.places_client')
    def test_find_suggestions_returns_options(self, mock_places, mock_db, mock_resolve, app, client):
        """POST /find_suggestions returns formatted Slack options."""
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_resolve.return_value = {'id': 1, 'lat_lng': '59.3419,18.0645'}
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
        mock_db.get_votes.return_value = []

        payload = json.dumps({'value': 'pizza', 'team': {'id': 'T123'}, 'channel': {'id': 'C1'}})
        response = client.post('/find_suggestions', data={'payload': payload})

        assert response.status_code == 200
        data = response.get_json()
        assert 'options' in data
        assert len(data['options']) == 2
        option = data['options'][0]
        assert option['value'] == 'ChIJ_pizza1'
        assert 'Pizza Place' in option['text']['text']
        assert 'open' in option['text']['text']
        assert '4.2' in option['text']['text']
        assert 'Add "pizza" as a custom restaurant' in data['options'][1]['text']['text']
        mock_db.save_restaurants.assert_called_once_with(
            mock_places.find_suggestion.return_value, 1, workspace_id='T123',
        )

    @patch('lunchbot.blueprints.slack_actions.resolve_location_for_channel')
    @patch('lunchbot.blueprints.slack_actions.db_client')
    @patch('lunchbot.blueprints.slack_actions.places_client')
    def test_find_suggestions_closed_restaurant(self, mock_places, mock_db, mock_resolve, app, client):
        """Closed restaurant shows 'closed' in option text."""
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_resolve.return_value = {'id': 1, 'lat_lng': '59.3419,18.0645'}
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
        mock_db.get_votes.return_value = []

        payload = json.dumps({'value': 'sushi', 'team': {'id': 'T123'}, 'channel': {'id': 'C1'}})
        response = client.post('/find_suggestions', data={'payload': payload})

        data = response.get_json()
        assert 'closed' in data['options'][0]['text']['text']

    @patch('lunchbot.blueprints.slack_actions.resolve_location_for_channel')
    @patch('lunchbot.blueprints.slack_actions.db_client')
    @patch('lunchbot.blueprints.slack_actions.places_client')
    def test_find_suggestions_unbound_channel_returns_none(
        self, mock_places, mock_db, mock_resolve, app, client,
    ):
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_resolve.return_value = None
        payload = json.dumps({
            'value': 'pizza', 'team': {'id': 'T123'}, 'channel': {'id': 'C1'},
        })

        response = client.post('/find_suggestions', data={'payload': payload})

        assert response.get_json() == {'options': []}
        mock_places.find_suggestion.assert_not_called()

    @patch('lunchbot.blueprints.slack_actions.resolve_location_for_channel')
    @patch('lunchbot.blueprints.slack_actions.db_client')
    @patch('lunchbot.blueprints.slack_actions.places_client')
    def test_find_suggestions_excludes_current_poll_options(
        self, mock_places, mock_db, mock_resolve, app, client,
    ):
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_resolve.return_value = {'id': 7, 'lat_lng': '59.3,18.0'}
        mock_places.find_suggestion.return_value = {
            'results': [
                {'place_id': 'existing', 'name': 'Existing'},
                {'place_id': 'new', 'name': 'New Place'},
            ],
        }
        mock_db.get_votes.return_value = [{'place_id': 'existing'}]
        payload = json.dumps({
            'value': 'place', 'team': {'id': 'T123'}, 'channel': {'id': 'C1'},
        })

        response = client.post('/find_suggestions', data={'payload': payload})
        values = [option['value'] for option in response.get_json()['options']]

        assert 'existing' not in values
        assert 'new' in values


class TestSuggestFunction:
    """Tests for suggest() called from external_select action."""

    @patch('lunchbot.blueprints.slack_actions.db_client')
    @patch('lunchbot.blueprints.slack_actions.places_client')
    def test_suggest_creates_poll_option(self, mock_places, mock_db, app, client):
        """External select action calls suggest which upserts poll option."""
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_db.get_restaurant_for_channel.return_value = {
            'id': 5, 'place_id': 'ChIJ_abc', 'name': 'Test',
            'url': 'https://example.com', 'location_id': 9, 'types': [],
        }
        mock_db.upsert_suggestion.return_value = 1

        payload = {
            'type': 'block_actions',
            'team': {'id': 'T123'},
            'channel': {'id': 'C123'},
            'message': {'ts': '123.456'},
            'actions': [{
                'type': 'external_select',
                'action_id': 'poll_add_restaurant',
                'selected_option': {'value': 'ChIJ_abc'},
            }],
        }
        with patch(
            'lunchbot.blueprints.slack_actions.resolve_location_for_channel',
            return_value={'id': 9, 'lat_lng': '59.3,18.0'},
        ), patch('lunchbot.blueprints.slack_actions._refresh_poll_message'):
            response = client.post('/action', data={
                'payload': json.dumps(payload)
            })

        assert response.status_code == 200
        mock_db.get_restaurant_for_channel.assert_called_once_with(
            'ChIJ_abc', 'T123', 'C123',
        )
        mock_db.upsert_suggestion.assert_called_once_with(
            date.today(), 5, 'T123', 'C123', pick_type='manual', cuisine=None,
        )

    @patch('lunchbot.blueprints.slack_actions.db_client')
    @patch('lunchbot.blueprints.slack_actions.places_client')
    def test_suggest_fetches_details_when_no_url(self, mock_places, mock_db, app, client):
        """suggest() fetches details and updates URL when restaurant has no url."""
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_db.get_restaurant_for_channel.return_value = {
            'id': 5, 'place_id': 'ChIJ_abc', 'name': 'Test', 'url': None,
            'location_id': 9, 'types': [],
        }
        mock_places.get_details.return_value = {
            'result': {'url': 'https://maps.google.com/abc', 'website': 'https://test.com'}
        }
        mock_db.update_restaurant_url.return_value = {}
        mock_db.upsert_suggestion.return_value = 1

        payload = {
            'type': 'block_actions',
            'team': {'id': 'T123'},
            'channel': {'id': 'C123'},
            'actions': [{
                'type': 'external_select',
                'action_id': 'poll_add_restaurant',
                'selected_option': {'value': 'ChIJ_abc'},
            }],
        }
        with patch(
            'lunchbot.blueprints.slack_actions.resolve_location_for_channel',
            return_value={'id': 9, 'lat_lng': '59.3,18.0'},
        ), patch('lunchbot.blueprints.slack_actions._refresh_poll_message'):
            response = client.post('/action', data={
                'payload': json.dumps(payload)
            })

        assert response.status_code == 200
        mock_places.get_details.assert_called_once_with('ChIJ_abc')
        mock_db.update_restaurant_url.assert_called_once_with(
            'ChIJ_abc', 'https://maps.google.com/abc', 'https://test.com',
            location_id=9,
        )


class TestCustomRestaurantSelection:
    @patch('lunchbot.blueprints.slack_actions.resolve_location_for_channel')
    @patch('lunchbot.blueprints.slack_actions.slack_client')
    def test_custom_option_opens_prefilled_modal(
        self, mock_slack, mock_resolve, app, client,
    ):
        from lunchbot.services.restaurant_selector_service import encode_custom_option

        app.config['SLACK_SIGNING_SECRET'] = None
        mock_resolve.return_value = {'id': 4, 'lat_lng': '59.3,18.0'}
        payload = {
            'type': 'block_actions',
            'team': {'id': 'T123'},
            'channel': {'id': 'C123'},
            'message': {'ts': '123.456'},
            'trigger_id': 'trigger',
            'actions': [{
                'type': 'external_select',
                'action_id': 'poll_add_restaurant',
                'selected_option': {'value': encode_custom_option('Cafe Test')},
            }],
        }

        response = client.post('/action', data={'payload': json.dumps(payload)})

        assert response.status_code == 200
        modal = mock_slack.views_open.call_args.args[1]
        assert modal['callback_id'] == 'modal_add_custom_restaurant'
        assert modal['blocks'][0]['element']['initial_value'] == 'Cafe Test'

    @patch('lunchbot.blueprints.slack_actions._refresh_poll_message')
    @patch('lunchbot.blueprints.slack_actions.db_client')
    @patch('lunchbot.blueprints.slack_actions.resolve_location_for_channel')
    def test_custom_modal_saves_to_bound_office(
        self, mock_resolve, mock_db, mock_refresh, app, client,
    ):
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_resolve.return_value = {'id': 42, 'lat_lng': '59.3,18.0'}
        mock_db.save_custom_restaurant.return_value = {'id': 88}
        mock_db.upsert_suggestion.return_value = 12
        payload = {
            'type': 'view_submission',
            'team': {'id': 'T123'},
            'user': {'id': 'U1'},
            'view': {
                'callback_id': 'modal_add_custom_restaurant',
                'private_metadata': json.dumps({
                    'team_id': 'T123', 'channel_id': 'C123',
                    'message_ts': '123.456',
                }),
                'state': {'values': {
                    'name': {'custom_restaurant_name': {'value': '  Cafe   Test  '}},
                    'address': {'custom_restaurant_address': {'value': 'Street 1'}},
                    'url': {'custom_restaurant_url': {'value': 'https://example.com'}},
                    'cuisine': {'custom_restaurant_cuisine': {'value': 'Cafe'}},
                }},
            },
        }

        response = client.post('/action', data={'payload': json.dumps(payload)})

        assert response.status_code == 200
        mock_db.save_custom_restaurant.assert_called_once_with(
            'Cafe Test', 42, 'T123', vicinity='Street 1',
            website='https://example.com', cuisine='Cafe',
        )
        mock_db.upsert_suggestion.assert_called_once_with(
            date.today(), 88, 'T123', 'C123',
            pick_type='manual', cuisine='Cafe',
        )
        mock_refresh.assert_called_once_with('T123', 'C123', '123.456')
