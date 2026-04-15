"""Tests for /slack/setup Places-autocomplete install flow."""
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.db


def test_setup_form_renders_places_widget(client):
    response = client.get('/slack/setup?team_id=T_X')
    assert response.status_code == 200
    body = response.data.decode()
    assert '/places/autocomplete' in body
    assert 'name="place_id"' in body
    # Legacy raw-coordinate input must be gone
    assert 'placeholder="59.3419' not in body
    assert 'name="coords"' not in body


@patch('lunchbot.blueprints.setup.threading.Thread')
@patch('lunchbot.blueprints.setup.create_workspace_location')
@patch('lunchbot.blueprints.setup.get_workspace')
@patch('lunchbot.blueprints.setup.places_client')
def test_setup_post_creates_office_and_seeds(
    mock_places, mock_get_ws, mock_create, mock_thread, client,
):
    mock_get_ws.return_value = {'team_id': 'T_X'}
    mock_places.get_place_details.return_value = {
        'result': {
            'place_id': 'P1',
            'name': 'Spotify HQ',
            'formatted_address': 'Regeringsgatan 19, 111 53 Stockholm, Sweden',
            'geometry': {'location': {'lat': 59.33, 'lng': 18.06}},
        },
        'status': 'OK',
    }
    mock_create.return_value = {
        'id': 7, 'team_id': 'T_X', 'name': 'Spotify HQ, Regeringsgatan 19',
        'lat_lng': '59.33,18.06', 'is_default': True,
    }

    response = client.post('/slack/setup', data={
        'team_id': 'T_X',
        'place_id': 'P1',
        'session_token': 'tok',
    })
    assert response.status_code == 200
    mock_places.get_place_details.assert_called_once_with('P1', session_token='tok')
    mock_create.assert_called_once()
    args, kwargs = mock_create.call_args
    assert args[0] == 'T_X'
    assert 'Spotify HQ' in args[1]
    assert args[2] == '59.33,18.06'
    assert kwargs.get('is_default') is True
    mock_thread.assert_called_once()


@patch('lunchbot.blueprints.setup.get_workspace')
def test_setup_post_missing_place_id(mock_get_ws, client):
    response = client.post('/slack/setup', data={'team_id': 'T_X'})
    assert response.status_code == 400


@patch('lunchbot.blueprints.setup.get_workspace')
def test_setup_post_unknown_workspace(mock_get_ws, client):
    mock_get_ws.return_value = None
    response = client.post('/slack/setup', data={'team_id': 'T_X', 'place_id': 'P1'})
    assert response.status_code == 400


@patch('lunchbot.blueprints.setup.create_workspace_location')
@patch('lunchbot.blueprints.setup.get_workspace')
@patch('lunchbot.blueprints.setup.places_client')
def test_setup_post_unresolvable_place(mock_places, mock_get_ws, mock_create, client):
    mock_get_ws.return_value = {'team_id': 'T_X'}
    mock_places.get_place_details.return_value = {'result': {}, 'status': 'OK'}
    response = client.post('/slack/setup', data={'team_id': 'T_X', 'place_id': 'P1'})
    assert response.status_code == 400
    mock_create.assert_not_called()


def test_setup_does_not_import_legacy_writer():
    """workspaces.location must not be written from setup.py anymore."""
    from lunchbot.blueprints import setup as setup_module
    assert not hasattr(setup_module, 'update_workspace_location')
