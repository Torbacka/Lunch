"""Tests for App Home service — Block Kit builders, modal constructors, and handlers."""
import json
import pytest
from unittest.mock import patch, MagicMock


class TestBuildHomeViewStateA:
    """State A: fresh workspace with no settings configured."""

    def test_state_a_with_none_settings(self):
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view(None)
        assert view['type'] == 'home'
        blocks_text = json.dumps(view['blocks'])
        assert 'Welcome to LunchBot!' in blocks_text
        assert 'Begin Setup' in blocks_text

    def test_state_a_with_no_channel(self):
        from lunchbot.services.app_home_service import build_home_view
        settings = {'team_id': 'T123', 'poll_channel': None}
        view = build_home_view(settings)
        blocks_text = json.dumps(view['blocks'])
        assert 'Welcome to LunchBot!' in blocks_text

    def test_state_a_has_primary_button(self):
        from lunchbot.services.app_home_service import build_home_view, ACTION_BEGIN_SETUP
        view = build_home_view(None)
        blocks_text = json.dumps(view['blocks'])
        assert ACTION_BEGIN_SETUP in blocks_text
        # Find the button and check it has primary style
        for block in view['blocks']:
            if block.get('type') == 'actions':
                for elem in block.get('elements', []):
                    if elem.get('action_id') == ACTION_BEGIN_SETUP:
                        assert elem.get('style') == 'primary'

    def test_state_a_non_admin_has_no_buttons(self):
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view(None, is_admin=False)
        blocks_text = json.dumps(view['blocks'])
        assert 'Begin Setup' not in blocks_text
        # No actions blocks
        action_blocks = [b for b in view['blocks'] if b.get('type') == 'actions']
        assert len(action_blocks) == 0


class TestBuildHomeViewStateB:
    """State B: configured workspace with channel set."""

    def _settings(self, **overrides):
        base = {
            'team_id': 'T123',
            'poll_channel': 'C_LUNCH',
            'poll_schedule_time': None,
            'poll_schedule_timezone': None,
            'poll_schedule_weekdays': None,
            'poll_size': 5,
            'smart_picks': 2,
            'location': 'Stockholm, Sweden',
        }
        base.update(overrides)
        return base

    def test_state_b_shows_channel(self):
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view(self._settings())
        blocks_text = json.dumps(view['blocks'])
        assert 'C_LUNCH' in blocks_text
        assert 'Poll Channel' in blocks_text

    def test_state_b_shows_edit_buttons(self):
        from lunchbot.services.app_home_service import (
            build_home_view, ACTION_EDIT_CHANNEL, ACTION_EDIT_SCHEDULE,
            ACTION_EDIT_POLL_SIZE, ACTION_ADD_OFFICE_FROM_HOME,
        )
        view = build_home_view(self._settings())
        blocks_text = json.dumps(view['blocks'])
        assert ACTION_EDIT_CHANNEL in blocks_text
        assert ACTION_EDIT_POLL_SIZE in blocks_text
        # Phase 07.1 Plan 06: legacy Location row replaced by Offices section
        assert ACTION_ADD_OFFICE_FROM_HOME in blocks_text

    def test_state_b_no_schedule_shows_message(self):
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view(self._settings())
        blocks_text = json.dumps(view['blocks'])
        assert 'No schedule configured' in blocks_text

    def test_state_b_with_schedule(self):
        from lunchbot.services.app_home_service import build_home_view
        from datetime import time
        settings = self._settings(
            poll_schedule_time=time(11, 30),
            poll_schedule_timezone='Europe/Stockholm',
            poll_schedule_weekdays=['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
        )
        view = build_home_view(settings)
        blocks_text = json.dumps(view['blocks'])
        assert '11:30 AM' in blocks_text
        assert 'Europe/Stockholm' in blocks_text
        assert 'Mon' in blocks_text

    def test_state_b_with_schedule_shows_remove_button(self):
        from lunchbot.services.app_home_service import (
            build_home_view, ACTION_REMOVE_SCHEDULE,
        )
        from datetime import time
        settings = self._settings(
            poll_schedule_time=time(11, 30),
            poll_schedule_timezone='Europe/Stockholm',
            poll_schedule_weekdays=['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
        )
        view = build_home_view(settings)
        blocks_text = json.dumps(view['blocks'])
        assert ACTION_REMOVE_SCHEDULE in blocks_text

    def test_state_b_non_admin_no_buttons(self):
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view(self._settings(), is_admin=False)
        blocks_text = json.dumps(view['blocks'])
        # No admin edit buttons for channel / schedule / poll_size / office mutations
        assert 'app_home_edit_channel' not in blocks_text
        assert 'app_home_edit_schedule' not in blocks_text
        assert 'app_home_edit_poll_size' not in blocks_text
        assert 'app_home_rename_office' not in blocks_text
        assert 'app_home_delete_office' not in blocks_text
        assert 'app_home_set_default_office' not in blocks_text
        # The only actions block allowed for non-admins is the Offices "Add office" button
        action_blocks = [b for b in view['blocks'] if b.get('type') == 'actions']
        assert len(action_blocks) == 1
        assert action_blocks[0]['elements'][0]['action_id'] == 'app_home_add_office'
        # Shows non-admin notice
        assert 'Contact a workspace admin' in blocks_text

    def test_state_b_poll_size_display(self):
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view(self._settings(poll_size=5, smart_picks=2))
        blocks_text = json.dumps(view['blocks'])
        assert '5 options' in blocks_text
        assert '2 smart picks' in blocks_text
        assert '3 random' in blocks_text

    def test_state_b_offices_section_rendered(self):
        # Phase 07.1 Plan 06: single Location row replaced by Offices section.
        from lunchbot.services.app_home_service import build_home_view
        locs = [{'id': 1, 'name': 'HQ', 'lat_lng': '59,18', 'is_default': True}]
        view = build_home_view(self._settings(), locations=locs)
        blocks_text = json.dumps(view['blocks'])
        assert 'Offices' in blocks_text
        assert 'HQ' in blocks_text

    def test_state_b_offices_section_empty_state(self):
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view(self._settings(), locations=[])
        blocks_text = json.dumps(view['blocks'])
        assert 'No offices yet' in blocks_text


class TestBuildChannelModal:
    def test_channel_modal_structure(self):
        from lunchbot.services.app_home_service import build_channel_modal, CALLBACK_CHANNEL
        modal = build_channel_modal(team_id='T123')
        assert modal['type'] == 'modal'
        assert modal['callback_id'] == CALLBACK_CHANNEL
        assert modal['title']['text'] == 'Poll Channel'
        assert modal['submit']['text'] == 'Save Channel'
        assert modal['close']['text'] == 'Keep Current Channel'
        # Has conversations_select input
        blocks_text = json.dumps(modal['blocks'])
        assert 'conversations_select' in blocks_text

    def test_channel_modal_with_current_value(self):
        from lunchbot.services.app_home_service import build_channel_modal
        modal = build_channel_modal(current_channel='C_EXISTING', team_id='T123')
        blocks_text = json.dumps(modal['blocks'])
        assert 'C_EXISTING' in blocks_text

    def test_channel_modal_has_private_metadata(self):
        from lunchbot.services.app_home_service import build_channel_modal
        modal = build_channel_modal(team_id='T123')
        metadata = json.loads(modal['private_metadata'])
        assert metadata['team_id'] == 'T123'


class TestBuildScheduleModal:
    def test_schedule_modal_structure(self):
        from lunchbot.services.app_home_service import build_schedule_modal, CALLBACK_SCHEDULE
        modal = build_schedule_modal(team_id='T123')
        assert modal['type'] == 'modal'
        assert modal['callback_id'] == CALLBACK_SCHEDULE
        assert modal['title']['text'] == 'Poll Schedule'
        assert modal['submit']['text'] == 'Save Schedule'
        assert modal['close']['text'] == 'Keep Current Schedule'
        blocks_text = json.dumps(modal['blocks'])
        assert 'timepicker' in blocks_text
        assert 'static_select' in blocks_text
        assert 'checkboxes' in blocks_text

    def test_schedule_modal_defaults(self):
        from lunchbot.services.app_home_service import build_schedule_modal
        modal = build_schedule_modal(team_id='T123')
        blocks_text = json.dumps(modal['blocks'])
        assert '11:30' in blocks_text
        assert 'Europe/Stockholm' in blocks_text


class TestBuildPollSizeModal:
    def test_poll_size_modal_structure(self):
        from lunchbot.services.app_home_service import build_poll_size_modal, CALLBACK_POLL_SIZE
        modal = build_poll_size_modal(team_id='T123')
        assert modal['type'] == 'modal'
        assert modal['callback_id'] == CALLBACK_POLL_SIZE
        assert modal['title']['text'] == 'Poll Options'
        assert modal['submit']['text'] == 'Save Options'
        assert modal['close']['text'] == 'Keep Current Options'
        blocks_text = json.dumps(modal['blocks'])
        assert 'static_select' in blocks_text
        assert 'Smart picks use your team' in blocks_text


# TestBuildLocationModal removed in Phase 07.1 Plan 06 — legacy single-location
# modal replaced by Offices section (rename/delete/add-office modals tested in
# tests/test_app_home_offices.py and tests/test_always_prompt_and_add_office.py).


class TestBuildRemoveScheduleModal:
    def test_remove_schedule_modal_structure(self):
        from lunchbot.services.app_home_service import (
            build_remove_schedule_modal, CALLBACK_REMOVE_SCHEDULE,
        )
        modal = build_remove_schedule_modal(team_id='T123')
        assert modal['type'] == 'modal'
        assert modal['callback_id'] == CALLBACK_REMOVE_SCHEDULE
        assert modal['title']['text'] == 'Remove Schedule'
        assert modal['submit']['text'] == 'Remove Schedule'
        assert modal['close']['text'] == 'Keep Schedule'
        blocks_text = json.dumps(modal['blocks'])
        assert 'Are you sure you want to remove the automatic poll schedule?' in blocks_text


class TestAppHomeOpenedEvent:
    """Test app_home_opened event handler."""

    @patch('lunchbot.blueprints.events.slack_client')
    @patch('lunchbot.blueprints.events.get_workspace_settings')
    @patch('lunchbot.blueprints.events._is_workspace_admin')
    def test_app_home_opened_publishes_view(self, mock_admin, mock_settings, mock_slack, app, client):
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_admin.return_value = True
        mock_settings.return_value = None
        mock_slack.views_publish.return_value = {'ok': True}

        response = client.post('/slack/events', json={
            'type': 'event_callback',
            'team_id': 'T123',
            'event': {'type': 'app_home_opened', 'user': 'U456'},
        })
        assert response.status_code == 200
        mock_slack.views_publish.assert_called_once()
        call_args = mock_slack.views_publish.call_args
        assert call_args[0][0] == 'U456'  # user_id
        assert call_args[0][1]['type'] == 'home'  # view
        assert call_args[0][2] == 'T123'  # team_id


class TestBlockActionsEditChannel:
    """Test App Home edit button opens channel modal."""

    @patch('lunchbot.blueprints.slack_actions.slack_client')
    @patch('lunchbot.blueprints.slack_actions.get_workspace_settings')
    def test_edit_channel_opens_modal(self, mock_settings, mock_slack, app, client):
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_settings.return_value = {'poll_channel': 'C_OLD'}
        mock_slack.views_open.return_value = {'ok': True}

        payload = {
            'type': 'block_actions',
            'team': {'id': 'T123'},
            'user': {'id': 'U456'},
            'trigger_id': 'trig_123',
            'actions': [{'action_id': 'app_home_edit_channel', 'type': 'button'}],
        }
        response = client.post('/action', data={'payload': json.dumps(payload)})
        assert response.status_code == 200
        mock_slack.views_open.assert_called_once()
        call_args = mock_slack.views_open.call_args
        assert call_args[0][0] == 'trig_123'  # trigger_id
        assert call_args[0][1]['callback_id'] == 'modal_channel'


class TestViewSubmissionChannel:
    """Test channel modal submission saves and refreshes."""

    @patch('lunchbot.blueprints.slack_actions.slack_client')
    @patch('lunchbot.blueprints.slack_actions.get_workspace_settings')
    @patch('lunchbot.blueprints.slack_actions.update_workspace_settings')
    def test_channel_submission_saves(self, mock_update, mock_get, mock_slack, app, client):
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_get.return_value = {'poll_channel': 'C_NEW'}
        mock_slack.views_publish.return_value = {'ok': True}

        payload = {
            'type': 'view_submission',
            'user': {'id': 'U456'},
            'view': {
                'callback_id': 'modal_channel',
                'private_metadata': json.dumps({'team_id': 'T123'}),
                'state': {
                    'values': {
                        'channel_select_block': {
                            'channel_select': {'selected_conversation': 'C_NEW'}
                        }
                    }
                },
            },
        }
        response = client.post('/action', data={'payload': json.dumps(payload)})
        assert response.status_code == 200
        mock_update.assert_called_once_with('T123', poll_channel='C_NEW')
        mock_slack.views_publish.assert_called_once()


class TestViewSubmissionPollSizeValidation:
    """Test poll size validation: smart >= total returns error."""

    def test_smart_picks_gte_total_returns_error(self, app, client):
        app.config['SLACK_SIGNING_SECRET'] = None
        payload = {
            'type': 'view_submission',
            'user': {'id': 'U456'},
            'view': {
                'callback_id': 'modal_poll_size',
                'private_metadata': json.dumps({'team_id': 'T123'}),
                'state': {
                    'values': {
                        'poll_total_block': {
                            'poll_total': {'selected_option': {'value': '3'}}
                        },
                        'smart_count_block': {
                            'smart_count': {'selected_option': {'value': '3'}}
                        },
                    }
                },
            },
        }
        response = client.post('/action', data={'payload': json.dumps(payload)})
        assert response.status_code == 200
        data = response.get_json()
        assert data['response_action'] == 'errors'
        assert 'smart_count_block' in data['errors']


class TestViewSubmissionSchedule:
    """Test schedule modal submission saves and syncs scheduler."""

    @patch('lunchbot.blueprints.slack_actions.slack_client')
    @patch('lunchbot.blueprints.slack_actions.update_schedule_job')
    @patch('lunchbot.blueprints.slack_actions.get_workspace_settings')
    @patch('lunchbot.blueprints.slack_actions.update_workspace_settings')
    def test_schedule_submission_saves_and_syncs(self, mock_update, mock_get, mock_sched, mock_slack, app, client):
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_get.return_value = {'poll_channel': 'C_LUNCH'}
        mock_slack.views_publish.return_value = {'ok': True}

        payload = {
            'type': 'view_submission',
            'user': {'id': 'U456'},
            'view': {
                'callback_id': 'modal_schedule',
                'private_metadata': json.dumps({'team_id': 'T123'}),
                'state': {
                    'values': {
                        'schedule_time_block': {
                            'schedule_time': {'selected_time': '11:30'}
                        },
                        'schedule_tz_block': {
                            'schedule_tz': {'selected_option': {'value': 'Europe/Stockholm'}}
                        },
                        'schedule_days_block': {
                            'schedule_days': {'selected_options': [
                                {'value': 'Mon'}, {'value': 'Wed'}, {'value': 'Fri'}
                            ]}
                        },
                    }
                },
            },
        }
        response = client.post('/action', data={'payload': json.dumps(payload)})
        assert response.status_code == 200
        mock_update.assert_called_once()
        mock_sched.assert_called_once()
        sched_args = mock_sched.call_args
        assert sched_args[0][0] == 'T123'
        assert sched_args[1]['channel'] == 'C_LUNCH'


class TestViewSubmissionRemoveSchedule:
    """Test remove schedule clears DB and removes scheduler job."""

    @patch('lunchbot.blueprints.slack_actions.slack_client')
    @patch('lunchbot.blueprints.slack_actions.remove_schedule_job')
    @patch('lunchbot.blueprints.slack_actions.get_workspace_settings')
    @patch('lunchbot.blueprints.slack_actions.update_workspace_settings')
    def test_remove_schedule_clears_and_removes_job(self, mock_update, mock_get, mock_remove, mock_slack, app, client):
        app.config['SLACK_SIGNING_SECRET'] = None
        mock_get.return_value = {'poll_channel': 'C_LUNCH'}
        mock_slack.views_publish.return_value = {'ok': True}

        payload = {
            'type': 'view_submission',
            'user': {'id': 'U456'},
            'view': {
                'callback_id': 'modal_remove_schedule',
                'private_metadata': json.dumps({'team_id': 'T123'}),
                'state': {'values': {}},
            },
        }
        response = client.post('/action', data={'payload': json.dumps(payload)})
        assert response.status_code == 200
        mock_update.assert_called_once_with(
            'T123',
            poll_schedule_time=None,
            poll_schedule_timezone=None,
            poll_schedule_weekdays=None,
        )
        mock_remove.assert_called_once_with('T123')
