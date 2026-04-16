"""Tests for Slack actions: channel picker, add-office modal (Phase 07.2 Plan 07)."""
import json
import pytest
from unittest.mock import patch, MagicMock


class TestListBotChannelsFiltersToMembers:
    """D-16: list_bot_channels uses users.conversations (bot-member channels only)."""

    @patch('lunchbot.client.slack_client.get_bot_token', return_value='xoxb-fake')
    def test_list_bot_channels_filters_to_members(self, mock_token, app):
        """users.conversations returns only bot-member channels; no extra filtering needed."""
        from lunchbot.client import slack_client

        fake_response = MagicMock()
        fake_response.json.return_value = {
            'ok': True,
            'channels': [
                {'id': 'C1', 'name': 'a'},
                {'id': 'C2', 'name': 'b'},
                {'id': 'C3', 'name': 'c'},
            ],
            'response_metadata': {'next_cursor': ''},
        }

        with app.app_context(), \
             patch.object(slack_client.session, 'get', return_value=fake_response) as mock_get:
            channels, next_cursor = slack_client.list_bot_channels('T1')

        # Assertion 1 (count): all 3 channels returned
        assert len(channels) == 3

        # Assertion 2 (endpoint): uses users.conversations, NOT conversations.list
        call_url = mock_get.call_args[0][0]
        assert 'users.conversations' in call_url, \
            "D-16: Must use users.conversations endpoint"
        assert 'conversations.list' not in call_url, \
            "Must NOT use conversations.list (would return non-member channels)"

        # Assertion 3 (shape): tuple with next_cursor
        assert next_cursor is None or next_cursor == ''


class TestAddOfficeModalSeedsWithLocation:
    """Add-office modal creates a workspace_location and binds the channel."""

    @patch('lunchbot.blueprints.slack_actions.slack_client')
    @patch('lunchbot.blueprints.slack_actions.places_client')
    @patch('lunchbot.blueprints.slack_actions.create_workspace_location')
    @patch('lunchbot.blueprints.slack_actions.list_workspace_locations', return_value=[])
    @patch('lunchbot.blueprints.slack_actions.bind_channel_location')
    @patch('lunchbot.blueprints.slack_actions.poll_service')
    def test_add_office_modal_seeds_with_location(
        self, mock_poll, mock_bind, mock_list_locs,
        mock_create_loc, mock_places, mock_slack, app, client,
    ):
        app.config['SLACK_SIGNING_SECRET'] = None

        # Mock places_client.get_place_details to return valid geometry
        mock_places.get_place_details.return_value = {
            'result': {
                'name': 'Test Office',
                'formatted_address': 'Street 1, City',
                'geometry': {'location': {'lat': 59.33, 'lng': 18.07}},
            },
        }

        # Mock create_workspace_location to return a row with an id
        mock_create_loc.return_value = {'id': 42, 'name': 'Test Office, Street 1'}
        mock_poll.push_poll.return_value = None

        payload = {
            'type': 'view_submission',
            'user': {'id': 'U456'},
            'view': {
                'callback_id': 'modal_add_office',
                'private_metadata': json.dumps({
                    'team_id': 'T123',
                    'channel_id': 'C_BOUND',
                }),
                'state': {
                    'values': {
                        'office_search_block': {
                            'office_search_select': {
                                'selected_option': {'value': 'ChIJxyz'},
                            },
                        },
                    },
                },
            },
        }
        response = client.post('/action', data={'payload': json.dumps(payload)})
        assert response.status_code == 200

        # Verify create_workspace_location was called with the newly created location
        mock_create_loc.assert_called_once()
        call_args = mock_create_loc.call_args
        assert call_args[0][0] == 'T123'  # team_id

        # Verify bind_channel_location was called with the new location_id
        mock_bind.assert_called_once_with('T123', 'C_BOUND', 42)
