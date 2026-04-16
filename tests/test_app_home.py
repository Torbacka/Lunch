"""Tests for App Home service -- Block Kit builders, modal constructors, and handlers.

Post-migration-009: Poll Channel and Poll Schedule moved to channel_schedules.
Legacy single-channel modals (channel, schedule, remove-schedule) replaced
by per-channel schedule modal (schedule_channel_modal).
"""
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

    def test_settings_present_renders_state_b(self):
        """When settings dict exists, render state B (configured workspace)."""
        from lunchbot.services.app_home_service import build_home_view
        settings = {'team_id': 'T123'}
        view = build_home_view(settings)
        blocks_text = json.dumps(view['blocks'])
        assert 'LunchBot Settings' in blocks_text
        assert 'Welcome to LunchBot!' not in blocks_text

    def test_state_a_has_primary_button(self):
        from lunchbot.services.app_home_service import build_home_view, ACTION_BEGIN_SETUP
        view = build_home_view(None)
        blocks_text = json.dumps(view['blocks'])
        assert ACTION_BEGIN_SETUP in blocks_text
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
        action_blocks = [b for b in view['blocks'] if b.get('type') == 'actions']
        assert len(action_blocks) == 0


class TestBuildHomeViewStateB:
    """State B: configured workspace."""

    def _settings(self, **overrides):
        base = {
            'team_id': 'T123',
            'poll_size': 5,
            'smart_picks': 2,
        }
        base.update(overrides)
        return base

    def test_state_b_shows_poll_size(self):
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view(self._settings())
        blocks_text = json.dumps(view['blocks'])
        assert '5 options' in blocks_text
        assert '2 smart picks' in blocks_text
        assert '3 random' in blocks_text

    def test_state_b_shows_edit_poll_size_button(self):
        from lunchbot.services.app_home_service import (
            build_home_view, ACTION_EDIT_POLL_SIZE, ACTION_ADD_OFFICE_FROM_HOME,
        )
        view = build_home_view(self._settings())
        blocks_text = json.dumps(view['blocks'])
        assert ACTION_EDIT_POLL_SIZE in blocks_text
        assert ACTION_ADD_OFFICE_FROM_HOME in blocks_text

    def test_state_b_non_admin_limited_buttons(self):
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view(self._settings(), is_admin=False)
        blocks_text = json.dumps(view['blocks'])
        assert 'app_home_edit_poll_size' not in blocks_text
        assert 'app_home_rename_office' not in blocks_text
        assert 'app_home_delete_office' not in blocks_text
        assert 'app_home_set_default_office' not in blocks_text
        assert 'Contact a workspace admin' in blocks_text

    def test_state_b_offices_section_rendered(self):
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

    def test_state_b_no_legacy_sections(self):
        """Post-009: no Poll Channel or Poll Schedule sections."""
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view(self._settings())
        blocks_text = json.dumps(view['blocks'])
        assert 'Poll Channel' not in blocks_text
        assert 'Poll Schedule' not in blocks_text


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
        assert call_args[0][0] == 'U456'
        assert call_args[0][1]['type'] == 'home'
        assert call_args[0][2] == 'T123'


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


# ---------------------------------------------------------------------------
# Phase 07.2 Plan 07: Per-channel schedule rendering tests
# ---------------------------------------------------------------------------

class TestBuildHomeViewPerChannelSchedules:
    """Verify build_home_view renders per-channel schedule rows."""

    def test_build_home_view_renders_per_channel_schedules(self):
        from lunchbot.services.app_home_service import build_home_view
        from datetime import time
        schedules = [
            {
                'channel_id': 'C1',
                'schedule_time': time(12, 0),
                'schedule_timezone': 'UTC',
                'schedule_weekdays': 'mon,tue',
            },
            {
                'channel_id': 'C2',
                'schedule_time': time(13, 0),
                'schedule_timezone': 'UTC',
                'schedule_weekdays': 'wed',
            },
        ]
        view = build_home_view({'poll_size': 5}, True, [], schedules)
        blocks_text = json.dumps(view['blocks'])
        assert '<#C1>' in blocks_text, "Channel C1 should appear in rendered view"
        assert '<#C2>' in blocks_text, "Channel C2 should appear in rendered view"
        assert 'open_schedule_channel_modal' in blocks_text, \
            "Schedule a channel button should be present"
        assert 'Poll Channel' not in blocks_text
        assert 'Poll Schedule' not in blocks_text

    def test_build_home_view_no_workspace_schedule_sections(self):
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view({'poll_size': 5}, True, [], [])
        blocks_text = json.dumps(view['blocks'])
        assert 'Poll Channel' not in blocks_text, \
            "Legacy Poll Channel section must not appear"
        assert 'Poll Schedule' not in blocks_text, \
            "Legacy Poll Schedule section must not appear"
