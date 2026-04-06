"""Tests for App Home service — Block Kit builders and modal constructors."""
import json
import pytest


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
            ACTION_EDIT_POLL_SIZE, ACTION_EDIT_LOCATION,
        )
        view = build_home_view(self._settings())
        blocks_text = json.dumps(view['blocks'])
        assert ACTION_EDIT_CHANNEL in blocks_text
        assert ACTION_EDIT_POLL_SIZE in blocks_text
        assert ACTION_EDIT_LOCATION in blocks_text

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
        # No edit buttons
        assert 'app_home_edit' not in blocks_text
        # No actions blocks
        action_blocks = [b for b in view['blocks'] if b.get('type') == 'actions']
        assert len(action_blocks) == 0
        # Shows non-admin notice
        assert 'Contact a workspace admin' in blocks_text

    def test_state_b_poll_size_display(self):
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view(self._settings(poll_size=5, smart_picks=2))
        blocks_text = json.dumps(view['blocks'])
        assert '5 options' in blocks_text
        assert '2 smart picks' in blocks_text
        assert '3 random' in blocks_text

    def test_state_b_location_display(self):
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view(self._settings())
        blocks_text = json.dumps(view['blocks'])
        assert 'Stockholm, Sweden' in blocks_text

    def test_state_b_no_location(self):
        from lunchbot.services.app_home_service import build_home_view
        view = build_home_view(self._settings(location=None))
        blocks_text = json.dumps(view['blocks'])
        assert 'Not set' in blocks_text


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


class TestBuildLocationModal:
    def test_location_modal_structure(self):
        from lunchbot.services.app_home_service import build_location_modal, CALLBACK_LOCATION
        modal = build_location_modal(team_id='T123')
        assert modal['type'] == 'modal'
        assert modal['callback_id'] == CALLBACK_LOCATION
        assert modal['title']['text'] == 'Search Location'
        assert modal['submit']['text'] == 'Save Location'
        assert modal['close']['text'] == 'Keep Current Location'
        blocks_text = json.dumps(modal['blocks'])
        assert 'plain_text_input' in blocks_text
        assert 'Stockholm, Sweden' in blocks_text


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
