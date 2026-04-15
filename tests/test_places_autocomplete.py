"""Tests for Places Autocomplete + Details client functions and proxy blueprint.

Phase 07.1 Plan 01: server-side Places Autocomplete proxy.
"""
from unittest.mock import patch, MagicMock


class TestPlacesClientAutocomplete:
    """Tests for lunchbot.client.places_client autocomplete/details/session-token helpers."""

    @patch('lunchbot.client.places_client.session')
    def test_autocomplete_calls_google_with_session_token(self, mock_session, app):
        """autocomplete() hits the autocomplete endpoint with session token and establishment type."""
        with app.app_context():
            app.config['GOOGLE_PLACES_API_KEY'] = 'test-key'
            mock_response = MagicMock()
            mock_response.json.return_value = {
                'status': 'OK',
                'predictions': [{'place_id': 'P1', 'description': 'Spotify HQ, Stockholm'}],
            }
            mock_session.get.return_value = mock_response

            from lunchbot.client.places_client import autocomplete
            result = autocomplete('Spotify', session_token='tok123')

            mock_session.get.assert_called_once()
            call_args = mock_session.get.call_args
            assert 'autocomplete/json' in call_args[0][0]
            params = call_args[1]['params']
            assert params['input'] == 'Spotify'
            assert params['sessiontoken'] == 'tok123'
            assert params['types'] == 'establishment'
            assert params['key'] == 'test-key'
            assert result['predictions'][0]['place_id'] == 'P1'

    @patch('lunchbot.client.places_client.session')
    def test_get_place_details_uses_field_mask(self, mock_session, app):
        """get_place_details() restricts fields to Basic tier only."""
        with app.app_context():
            app.config['GOOGLE_PLACES_API_KEY'] = 'test-key'
            mock_response = MagicMock()
            mock_response.json.return_value = {
                'status': 'OK',
                'result': {
                    'place_id': 'P1',
                    'name': 'Spotify HQ',
                    'formatted_address': 'Regeringsgatan 19',
                    'geometry': {'location': {'lat': 59.33, 'lng': 18.06}},
                },
            }
            mock_session.get.return_value = mock_response

            from lunchbot.client.places_client import get_place_details
            result = get_place_details('P1', session_token='tok123')

            call_args = mock_session.get.call_args
            assert 'details/json' in call_args[0][0]
            params = call_args[1]['params']
            assert params['placeid'] == 'P1'
            assert params['fields'] == 'place_id,name,formatted_address,geometry/location'
            assert params['sessiontoken'] == 'tok123'
            assert params['key'] == 'test-key'
            assert result['result']['place_id'] == 'P1'

    def test_new_session_token_unique(self, app):
        """new_session_token() returns unique 32-char hex strings."""
        from lunchbot.client.places_client import new_session_token
        t1 = new_session_token()
        t2 = new_session_token()
        assert isinstance(t1, str)
        assert len(t1) == 32
        assert len(t2) == 32
        assert t1 != t2
        # Hex only
        int(t1, 16)
        int(t2, 16)


class TestPlacesProxyBlueprint:
    """Tests for /places/autocomplete and /places/details proxy endpoints."""

    @patch('lunchbot.blueprints.places_proxy.places_client')
    def test_proxy_autocomplete_returns_predictions(self, mock_places, app, client):
        """GET /places/autocomplete returns normalized predictions + session_token."""
        app.config['SLACK_SIGNING_SECRET'] = None
        app.config['GOOGLE_PLACES_API_KEY'] = 'test-key'
        mock_places.autocomplete.return_value = {
            'status': 'OK',
            'predictions': [{
                'place_id': 'P1',
                'description': 'Spotify HQ, Stockholm',
                'structured_formatting': {
                    'main_text': 'Spotify HQ',
                    'secondary_text': 'Stockholm',
                },
            }],
        }
        mock_places.new_session_token.return_value = 'generated-tok'

        response = client.get('/places/autocomplete?q=Spotify')
        assert response.status_code == 200
        data = response.get_json()
        assert data['predictions'][0]['place_id'] == 'P1'
        assert data['predictions'][0]['main_text'] == 'Spotify HQ'
        assert data['predictions'][0]['secondary_text'] == 'Stockholm'
        assert 'session_token' in data

    @patch('lunchbot.blueprints.places_proxy.places_client')
    def test_proxy_autocomplete_missing_q(self, mock_places, app, client):
        """GET /places/autocomplete without q returns 400."""
        app.config['SLACK_SIGNING_SECRET'] = None
        response = client.get('/places/autocomplete')
        assert response.status_code == 400
        assert 'error' in response.get_json()
        mock_places.autocomplete.assert_not_called()

    @patch('lunchbot.blueprints.places_proxy.places_client')
    def test_proxy_details_returns_lat_lng(self, mock_places, app, client):
        """GET /places/details returns whitelisted fields including lat/lng."""
        app.config['SLACK_SIGNING_SECRET'] = None
        app.config['GOOGLE_PLACES_API_KEY'] = 'test-key'
        mock_places.get_place_details.return_value = {
            'status': 'OK',
            'result': {
                'place_id': 'P1',
                'name': 'Spotify HQ',
                'formatted_address': 'Regeringsgatan 19, Stockholm',
                'geometry': {'location': {'lat': 59.33, 'lng': 18.06}},
            },
        }
        response = client.get('/places/details?place_id=P1&session_token=tok')
        assert response.status_code == 200
        data = response.get_json()
        assert data['place_id'] == 'P1'
        assert data['name'] == 'Spotify HQ'
        assert data['formatted_address'] == 'Regeringsgatan 19, Stockholm'
        assert data['lat'] == 59.33
        assert data['lng'] == 18.06

    @patch('lunchbot.blueprints.places_proxy.places_client')
    def test_proxy_details_404_when_no_geometry(self, mock_places, app, client):
        """Missing geometry in Google response → 404."""
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_places.get_place_details.return_value = {
            'status': 'OK',
            'result': {'place_id': 'P1'},
        }
        response = client.get('/places/details?place_id=P1')
        assert response.status_code == 404

    @patch('lunchbot.blueprints.places_proxy.places_client')
    def test_proxy_details_missing_place_id(self, mock_places, app, client):
        """Missing place_id → 400."""
        app.config['SLACK_SIGNING_SECRET'] = None
        response = client.get('/places/details')
        assert response.status_code == 400
        mock_places.get_place_details.assert_not_called()

    @patch('lunchbot.blueprints.places_proxy.places_client')
    def test_proxy_does_not_leak_api_key(self, mock_places, app, client):
        """API key string must never appear in the response body."""
        app.config['SLACK_SIGNING_SECRET'] = None
        app.config['GOOGLE_PLACES_API_KEY'] = 'super-secret-key-xyz'
        mock_places.autocomplete.return_value = {
            'status': 'OK',
            'predictions': [{
                'place_id': 'P1',
                'description': 'Spotify HQ',
                'structured_formatting': {'main_text': 'Spotify HQ', 'secondary_text': ''},
            }],
        }
        mock_places.new_session_token.return_value = 'tok'
        response = client.get('/places/autocomplete?q=Spotify')
        assert b'super-secret-key-xyz' not in response.data
