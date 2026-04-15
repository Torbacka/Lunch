"""Tests for Phase 07.1 always-prompt + add-office flow."""
import json
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.db


# --- /lunch always-prompts ---

@patch('lunchbot.blueprints.polls.list_workspace_locations')
@patch('lunchbot.blueprints.polls.poll_service')
@patch('lunchbot.blueprints.polls.resolve_location_for_channel')
def test_lunch_unbound_single_office_still_prompts(
    mock_resolver, mock_poll_service, mock_list, client,
):
    mock_resolver.return_value = None
    mock_list.return_value = [{'id': 1, 'name': 'HQ', 'lat_lng': '59,18'}]
    response = client.post('/slack/command', data={
        'team_id': 'T1', 'command': '/lunch', 'text': '',
        'channel_id': 'C1', 'user_id': 'U1',
    })
    assert response.status_code == 200
    body = json.loads(response.data)
    blob = json.dumps(body)
    assert 'channel_loc_pick' in blob
    assert 'channel_loc_add_office' in blob
    mock_poll_service.push_poll.assert_not_called()


@patch('lunchbot.blueprints.polls.list_workspace_locations')
@patch('lunchbot.blueprints.polls.resolve_location_for_channel')
def test_lunch_unbound_zero_offices_shows_only_add(
    mock_resolver, mock_list, client,
):
    mock_resolver.return_value = None
    mock_list.return_value = []
    response = client.post('/slack/command', data={
        'team_id': 'T1', 'command': '/lunch', 'text': '',
        'channel_id': 'C1', 'user_id': 'U1',
    })
    assert response.status_code == 200
    body = json.loads(response.data)
    blob = json.dumps(body)
    assert 'channel_loc_add_office' in blob
    assert 'channel_loc_pick' not in blob


def test_build_add_office_modal_shape():
    from lunchbot.services.office_modal_service import (
        build_add_office_modal, CALLBACK_ADD_OFFICE, OFFICE_SEARCH_SELECT,
    )
    modal = build_add_office_modal('T1', 'C1')
    assert modal['type'] == 'modal'
    assert modal['callback_id'] == CALLBACK_ADD_OFFICE
    meta = json.loads(modal['private_metadata'])
    assert meta == {'team_id': 'T1', 'channel_id': 'C1'}
    el = modal['blocks'][0]['element']
    assert el['type'] == 'external_select'
    assert el['action_id'] == OFFICE_SEARCH_SELECT
    assert el['min_query_length'] == 3


def test_build_add_office_modal_no_channel():
    from lunchbot.services.office_modal_service import build_add_office_modal
    modal = build_add_office_modal('T1')
    meta = json.loads(modal['private_metadata'])
    assert meta == {'team_id': 'T1'}


# --- Task 2: Slack action wiring ---

@patch('lunchbot.blueprints.slack_actions.slack_client')
@patch('lunchbot.blueprints.slack_actions.build_add_office_modal')
def test_add_office_button_opens_modal(mock_build, mock_slack, client):
    mock_build.return_value = {'type': 'modal'}
    payload = {
        'type': 'block_actions',
        'team': {'id': 'T1'},
        'user': {'id': 'U1'},
        'channel': {'id': 'C1'},
        'trigger_id': 'TRIG',
        'actions': [{'action_id': 'channel_loc_add_office', 'type': 'button', 'value': 'C1'}],
    }
    response = client.post('/action', data={'payload': json.dumps(payload)})
    assert response.status_code == 200
    mock_build.assert_called_once_with('T1', channel_id='C1')
    mock_slack.views_open.assert_called_once()


@patch('lunchbot.blueprints.slack_actions.places_client')
def test_office_search_external_select_returns_options(mock_places, client):
    mock_places.new_session_token.return_value = 'tok'
    mock_places.autocomplete.return_value = {
        'predictions': [
            {'place_id': 'P1', 'description': 'Spotify HQ, Stockholm'},
            {'place_id': 'P2', 'description': 'Spotify NYC, New York'},
        ],
        'status': 'OK',
    }
    payload = {
        'action_id': 'office_search_select',
        'value': 'Spotify',
        'team': {'id': 'T1'},
        'channel': {'id': 'C1'},
    }
    response = client.post('/find_suggestions', data={'payload': json.dumps(payload)})
    assert response.status_code == 200
    body = json.loads(response.data)
    assert len(body['options']) == 2
    assert body['options'][0]['value'] == 'P1'


@patch('lunchbot.blueprints.slack_actions.poll_service')
@patch('lunchbot.blueprints.slack_actions.bind_channel_location')
@patch('lunchbot.blueprints.slack_actions.create_workspace_location')
@patch('lunchbot.blueprints.slack_actions.list_workspace_locations')
@patch('lunchbot.blueprints.slack_actions.places_client')
def test_modal_submission_creates_office_and_binds_channel(
    mock_places, mock_list, mock_create, mock_bind, mock_poll, client,
):
    mock_list.return_value = []  # first office
    mock_places.get_place_details.return_value = {
        'result': {
            'place_id': 'P1', 'name': 'Spotify HQ',
            'formatted_address': 'Regeringsgatan 19, 111 53 Stockholm',
            'geometry': {'location': {'lat': 59.33, 'lng': 18.06}},
        },
        'status': 'OK',
    }
    mock_create.return_value = {'id': 7, 'name': 'Spotify HQ, Regeringsgatan 19'}
    payload = {
        'type': 'view_submission',
        'team': {'id': 'T1'},
        'user': {'id': 'U1'},
        'view': {
            'callback_id': 'modal_add_office',
            'private_metadata': json.dumps({'team_id': 'T1', 'channel_id': 'C1'}),
            'state': {'values': {'office_search_block': {
                'office_search_select': {'selected_option': {'value': 'P1'}}
            }}},
        },
    }
    response = client.post('/action', data={'payload': json.dumps(payload)})
    assert response.status_code == 200
    mock_create.assert_called_once()
    args, kwargs = mock_create.call_args
    assert args[0] == 'T1'
    assert args[2] == '59.33,18.06'
    assert kwargs.get('is_default') is True  # first office for the workspace
    mock_bind.assert_called_once_with('T1', 'C1', 7)
    mock_poll.push_poll.assert_called_once()


@patch('lunchbot.blueprints.slack_actions.places_client')
def test_modal_submission_rejects_unresolvable_place(mock_places, client):
    mock_places.get_place_details.return_value = {'result': {}, 'status': 'OK'}
    payload = {
        'type': 'view_submission',
        'team': {'id': 'T1'},
        'user': {'id': 'U1'},
        'view': {
            'callback_id': 'modal_add_office',
            'private_metadata': json.dumps({'team_id': 'T1', 'channel_id': 'C1'}),
            'state': {'values': {'office_search_block': {
                'office_search_select': {'selected_option': {'value': 'P1'}}
            }}},
        },
    }
    response = client.post('/action', data={'payload': json.dumps(payload)})
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body.get('response_action') == 'errors'
