"""Tests for the App Home Offices section (Phase 07.1 Plan 06)."""
import json
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.db


def _find_blocks_with(blocks, predicate):
    return [b for b in blocks if predicate(b)]


# --- Task 1: rendering tests ---


def test_offices_section_renders_each_location_with_admin_buttons():
    from lunchbot.services.app_home_service import build_home_view
    settings = {'poll_channel': 'C1', 'poll_size': 5, 'smart_picks': 2}
    locs = [
        {'id': 1, 'name': 'HQ', 'lat_lng': '59,18', 'is_default': True},
        {'id': 2, 'name': 'Branch', 'lat_lng': '60,18', 'is_default': False},
    ]
    view = build_home_view(settings, is_admin=True, locations=locs)
    blob = json.dumps(view)
    assert 'HQ' in blob and 'Branch' in blob
    assert 'app_home_add_office' in blob
    assert 'app_home_rename_office' in blob
    assert 'app_home_delete_office' in blob
    # Set default button only on Branch (HQ is already default)
    assert blob.count('app_home_set_default_office') == 1
    assert ':star:' in blob  # default marker on HQ


def test_offices_section_non_admin_hides_mutating_buttons_but_shows_add():
    from lunchbot.services.app_home_service import build_home_view
    settings = {'poll_channel': 'C1', 'poll_size': 5, 'smart_picks': 2}
    locs = [{'id': 1, 'name': 'HQ', 'lat_lng': '59,18', 'is_default': True}]
    view = build_home_view(settings, is_admin=False, locations=locs)
    blob = json.dumps(view)
    assert 'app_home_add_office' in blob  # Add is always allowed
    assert 'app_home_rename_office' not in blob
    assert 'app_home_delete_office' not in blob
    assert 'app_home_set_default_office' not in blob


def test_offices_section_empty_state():
    from lunchbot.services.app_home_service import build_home_view
    settings = {'poll_channel': 'C1', 'poll_size': 5, 'smart_picks': 2}
    view = build_home_view(settings, is_admin=True, locations=[])
    blob = json.dumps(view)
    assert 'No offices yet' in blob
    assert 'app_home_add_office' in blob


def test_legacy_location_section_removed():
    """The single-location section and modal must be gone."""
    from lunchbot.services import app_home_service
    assert not hasattr(app_home_service, 'build_location_modal')
    assert not hasattr(app_home_service, 'ACTION_EDIT_LOCATION')
    assert not hasattr(app_home_service, 'CALLBACK_LOCATION')


def test_build_rename_office_modal_shape():
    from lunchbot.services.app_home_service import (
        build_rename_office_modal, CALLBACK_RENAME_OFFICE,
    )
    modal = build_rename_office_modal('T1', 7, 'HQ')
    assert modal['callback_id'] == CALLBACK_RENAME_OFFICE
    meta = json.loads(modal['private_metadata'])
    assert meta == {'team_id': 'T1', 'location_id': 7}
    assert modal['blocks'][0]['element']['initial_value'] == 'HQ'


def test_build_delete_office_modal_shape():
    from lunchbot.services.app_home_service import (
        build_delete_office_modal, CALLBACK_DELETE_OFFICE,
    )
    modal = build_delete_office_modal('T1', 7, 'HQ')
    assert modal['callback_id'] == CALLBACK_DELETE_OFFICE
    meta = json.loads(modal['private_metadata'])
    assert meta == {'team_id': 'T1', 'location_id': 7, 'name': 'HQ'}
    assert 'HQ' in modal['blocks'][0]['text']['text']


# --- Task 2: action handler tests ---


@patch('lunchbot.blueprints.slack_actions.slack_client')
@patch('lunchbot.blueprints.slack_actions.list_workspace_locations')
def test_rename_button_admin_opens_modal(mock_list, mock_slack, client):
    mock_slack.is_workspace_admin.return_value = True
    mock_list.return_value = [
        {'id': 7, 'name': 'HQ', 'lat_lng': '59,18', 'is_default': True},
    ]
    payload = {
        'type': 'block_actions',
        'team': {'id': 'T1'}, 'user': {'id': 'U1'},
        'trigger_id': 'TRIG',
        'actions': [
            {'action_id': 'app_home_rename_office', 'type': 'button', 'value': '7'},
        ],
    }
    response = client.post('/action', data={'payload': json.dumps(payload)})
    assert response.status_code == 200
    mock_slack.views_open.assert_called_once()


@patch('lunchbot.blueprints.slack_actions.slack_client')
@patch('lunchbot.blueprints.slack_actions.delete_workspace_location')
def test_rename_button_non_admin_blocked(mock_delete, mock_slack, client):
    mock_slack.is_workspace_admin.return_value = False
    payload = {
        'type': 'block_actions',
        'team': {'id': 'T1'}, 'user': {'id': 'U1'},
        'trigger_id': 'TRIG',
        'actions': [
            {'action_id': 'app_home_rename_office', 'type': 'button', 'value': '7'},
        ],
    }
    response = client.post('/action', data={'payload': json.dumps(payload)})
    assert response.status_code == 200
    mock_slack.views_open.assert_not_called()


@patch('lunchbot.blueprints.slack_actions._refresh_app_home')
@patch('lunchbot.blueprints.slack_actions.slack_client')
@patch('lunchbot.blueprints.slack_actions.set_default_workspace_location')
@patch('lunchbot.blueprints.slack_actions.list_workspace_locations')
def test_set_default_admin_calls_helper(
    mock_list, mock_set, mock_slack, mock_refresh, client,
):
    mock_slack.is_workspace_admin.return_value = True
    mock_list.return_value = [
        {'id': 7, 'name': 'Branch', 'lat_lng': '60,18', 'is_default': False},
    ]
    payload = {
        'type': 'block_actions',
        'team': {'id': 'T1'}, 'user': {'id': 'U1'},
        'trigger_id': 'TRIG',
        'actions': [
            {'action_id': 'app_home_set_default_office', 'type': 'button', 'value': '7'},
        ],
    }
    response = client.post('/action', data={'payload': json.dumps(payload)})
    assert response.status_code == 200
    mock_set.assert_called_once_with('T1', 7, 'U1')
    mock_refresh.assert_called_once()


@patch('lunchbot.blueprints.slack_actions._refresh_app_home')
@patch('lunchbot.blueprints.slack_actions.slack_client')
@patch('lunchbot.blueprints.slack_actions.delete_workspace_location')
def test_delete_modal_submission_admin(
    mock_delete, mock_slack, mock_refresh, client,
):
    mock_slack.is_workspace_admin.return_value = True
    payload = {
        'type': 'view_submission',
        'team': {'id': 'T1'}, 'user': {'id': 'U1'},
        'view': {
            'callback_id': 'modal_delete_office',
            'private_metadata': json.dumps(
                {'team_id': 'T1', 'location_id': 7, 'name': 'HQ'}
            ),
            'state': {'values': {}},
        },
    }
    response = client.post('/action', data={'payload': json.dumps(payload)})
    assert response.status_code == 200
    mock_delete.assert_called_once_with('T1', 7, 'U1')
    mock_refresh.assert_called_once()


@patch('lunchbot.blueprints.slack_actions._refresh_app_home')
@patch('lunchbot.blueprints.slack_actions.slack_client')
@patch('lunchbot.blueprints.slack_actions.rename_workspace_location')
def test_rename_modal_submission_admin(
    mock_rename, mock_slack, mock_refresh, client,
):
    mock_slack.is_workspace_admin.return_value = True
    payload = {
        'type': 'view_submission',
        'team': {'id': 'T1'}, 'user': {'id': 'U1'},
        'view': {
            'callback_id': 'modal_rename_office',
            'private_metadata': json.dumps({'team_id': 'T1', 'location_id': 7}),
            'state': {
                'values': {
                    'office_name_block': {
                        'office_name_input': {'value': 'Spotify HQ'},
                    },
                },
            },
        },
    }
    response = client.post('/action', data={'payload': json.dumps(payload)})
    assert response.status_code == 200
    mock_rename.assert_called_once_with('T1', 7, 'Spotify HQ', 'U1')
