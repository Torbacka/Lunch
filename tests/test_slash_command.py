"""Tests for the /slack/command slash command endpoint."""
import json
from unittest.mock import patch, MagicMock


class TestSlashCommand:
    """Tests for POST /slack/command handler."""

    def test_slash_help(self, client):
        """POST /slack/command with text=help returns ephemeral JSON with help text."""
        response = client.post('/slack/command', data={
            'team_id': 'T123ABC',
            'command': '/lunch',
            'text': 'help',
            'channel_id': 'C123',
            'user_id': 'U123',
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['response_type'] == 'ephemeral'
        assert '/lunch' in data['text']
        assert 'help' in data['text']

    def test_slash_help_case_insensitive(self, client):
        """POST /slack/command with text=HELP should also return help."""
        response = client.post('/slack/command', data={
            'team_id': 'T123ABC',
            'command': '/lunch',
            'text': 'HELP',
            'channel_id': 'C123',
            'user_id': 'U123',
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['response_type'] == 'ephemeral'

    @patch('lunchbot.blueprints.polls.resolve_location_for_channel')
    @patch('lunchbot.blueprints.polls.poll_service')
    def test_slash_poll_trigger(self, mock_poll_service, mock_resolve, client):
        """POST /slack/command with empty text calls push_poll and returns 200."""
        mock_resolve.return_value = {'id': 1, 'lat_lng': '59,18'}
        mock_poll_service.push_poll.return_value = {'ok': True}
        response = client.post('/slack/command', data={
            'team_id': 'T123ABC',
            'command': '/lunch',
            'text': '',
            'channel_id': 'C123',
            'user_id': 'U123',
        })
        assert response.status_code == 200
        mock_poll_service.push_poll.assert_called_once_with('C123', 'T123ABC')

    @patch('lunchbot.blueprints.polls.resolve_location_for_channel')
    @patch('lunchbot.blueprints.polls.poll_service')
    def test_slash_unknown_command(self, mock_poll_service, mock_resolve, client):
        """POST /slack/command with text='nonsense' triggers poll (default behaviour)."""
        mock_resolve.return_value = {'id': 1, 'lat_lng': '59,18'}
        mock_poll_service.push_poll.return_value = {'ok': True}
        response = client.post('/slack/command', data={
            'team_id': 'T123ABC',
            'command': '/lunch',
            'text': 'nonsense',
            'channel_id': 'C123',
            'user_id': 'U123',
        })
        assert response.status_code == 200
        mock_poll_service.push_poll.assert_called_once_with('C123', 'T123ABC')

    @patch('lunchbot.blueprints.polls.resolve_location_for_channel')
    @patch('lunchbot.blueprints.polls.poll_service')
    def test_slash_no_workspace(self, mock_poll_service, mock_resolve, client):
        """push_poll raising ValueError returns ephemeral error message."""
        mock_resolve.return_value = {'id': 1, 'lat_lng': '59,18'}
        mock_poll_service.push_poll.side_effect = ValueError('No active workspace: T_MISSING')
        response = client.post('/slack/command', data={
            'team_id': 'T_MISSING',
            'command': '/lunch',
            'text': '',
            'channel_id': 'C123',
            'user_id': 'U123',
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['response_type'] == 'ephemeral'
        assert 'not configured' in data['text']
