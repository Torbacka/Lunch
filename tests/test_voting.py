"""Tests for vote_service and POST /action wiring."""
import json
from datetime import date
from unittest.mock import patch, MagicMock, call


SAMPLE_PAYLOAD = {
    'type': 'block_actions',
    'team': {'id': 'T123ABC'},
    'user': {'id': 'U456'},
    'channel': {'id': 'C123'},
    'message': {'ts': '1234567890.123456', 'blocks': []},
    'actions': [{'type': 'button', 'value': '42'}],
}

SAMPLE_OPTIONS = [
    {
        'id': 42,
        'restaurant_id': 10,
        'place_id': 'ChIJ_abc',
        'name': 'Pasta Palace',
        'rating': 4.5,
        'emoji': 'spaghetti',
        'url': 'https://maps.google.com/pasta',
        'website': 'https://pastapalace.com',
        'price_level': 2,
        'votes': ['U456'],
    },
]

SAMPLE_OPTIONS_NO_VOTES = [
    {
        'id': 42,
        'restaurant_id': 10,
        'place_id': 'ChIJ_abc',
        'name': 'Pasta Palace',
        'rating': 4.5,
        'emoji': 'spaghetti',
        'url': 'https://maps.google.com/pasta',
        'website': 'https://pastapalace.com',
        'price_level': 2,
        'votes': [],
    },
]

MOCK_PROFILE = {
    'image_24': 'https://avatars.slack.com/U456_24.jpg',
    'display_name': 'TestUser',
    'real_name': 'Test User',
}


class TestVoteService:
    """Tests for vote_service.vote()."""

    @patch('lunchbot.services.vote_service.slack_client')
    @patch('lunchbot.services.vote_service.poll_service')
    @patch('lunchbot.services.vote_service.db_client')
    def test_vote_adds(self, mock_db, mock_poll, mock_slack, app):
        """Toggle vote adds, rebuilds blocks, updates message."""
        with app.app_context():
            mock_db.toggle_vote.return_value = 'added'
            mock_db.get_votes.return_value = SAMPLE_OPTIONS
            mock_slack.get_user_profile.return_value = MOCK_PROFILE
            mock_slack.update_message.return_value = {'ok': True}
            mock_poll.build_poll_blocks.return_value = [{'type': 'section'}]

            from lunchbot.services.vote_service import vote
            # Clear cache for clean test
            import lunchbot.services.vote_service as vs
            vs.profile_cache.clear()

            vote(SAMPLE_PAYLOAD)

            mock_db.toggle_vote.assert_called_once_with(42, 'U456')
            mock_db.get_votes.assert_called_once_with(date.today())
            mock_slack.update_message.assert_called_once()
            call_args = mock_slack.update_message.call_args
            assert call_args[0][0] == 'C123'
            assert call_args[0][1] == '1234567890.123456'
            assert call_args[0][3] == 'T123ABC'

    @patch('lunchbot.services.vote_service.slack_client')
    @patch('lunchbot.services.vote_service.poll_service')
    @patch('lunchbot.services.vote_service.db_client')
    def test_vote_removes(self, mock_db, mock_poll, mock_slack, app):
        """Toggle vote removes, option has empty votes, 'No votes' in rebuilt blocks."""
        with app.app_context():
            mock_db.toggle_vote.return_value = 'removed'
            mock_db.get_votes.return_value = SAMPLE_OPTIONS_NO_VOTES
            mock_slack.update_message.return_value = {'ok': True}
            mock_poll.build_poll_blocks.return_value = [{'type': 'section'}]

            from lunchbot.services.vote_service import vote
            import lunchbot.services.vote_service as vs
            vs.profile_cache.clear()

            vote(SAMPLE_PAYLOAD)

            mock_db.toggle_vote.assert_called_once_with(42, 'U456')
            # No voter images fetched for empty votes
            mock_slack.get_user_profile.assert_not_called()
            mock_slack.update_message.assert_called_once()

    @patch('lunchbot.services.vote_service.slack_client')
    @patch('lunchbot.services.vote_service.poll_service')
    @patch('lunchbot.services.vote_service.db_client')
    def test_profile_cache(self, mock_db, mock_poll, mock_slack, app):
        """Calling vote twice with same user_id only calls get_user_profile once."""
        with app.app_context():
            mock_db.toggle_vote.return_value = 'added'
            mock_db.get_votes.return_value = SAMPLE_OPTIONS
            mock_slack.get_user_profile.return_value = MOCK_PROFILE
            mock_slack.update_message.return_value = {'ok': True}
            mock_poll.build_poll_blocks.return_value = [{'type': 'section'}]

            from lunchbot.services.vote_service import vote
            import lunchbot.services.vote_service as vs
            vs.profile_cache.clear()

            vote(SAMPLE_PAYLOAD)
            vote(SAMPLE_PAYLOAD)

            # get_user_profile called only once due to caching
            assert mock_slack.get_user_profile.call_count == 1

    @patch('lunchbot.services.vote_service.slack_client')
    @patch('lunchbot.services.vote_service.poll_service')
    @patch('lunchbot.services.vote_service.db_client')
    def test_voter_elements_built(self, mock_db, mock_poll, mock_slack, app):
        """Options passed to build_poll_blocks have voter_elements populated."""
        with app.app_context():
            mock_db.toggle_vote.return_value = 'added'
            mock_db.get_votes.return_value = [dict(SAMPLE_OPTIONS[0])]
            mock_slack.get_user_profile.return_value = MOCK_PROFILE
            mock_slack.update_message.return_value = {'ok': True}
            mock_poll.build_poll_blocks.return_value = [{'type': 'section'}]

            from lunchbot.services.vote_service import vote
            import lunchbot.services.vote_service as vs
            vs.profile_cache.clear()

            vote(SAMPLE_PAYLOAD)

            # Check options passed to build_poll_blocks have voter_elements
            options_passed = mock_poll.build_poll_blocks.call_args[0][0]
            assert 'voter_elements' in options_passed[0]
            elements = options_passed[0]['voter_elements']
            # Should have image element + count text element
            assert any(e.get('type') == 'image' for e in elements)
            assert any('1 vote' in e.get('text', '') for e in elements)


class TestActionEndpoint:
    """Tests for POST /action wiring to vote_service."""

    @patch('lunchbot.blueprints.slack_actions.vote_service')
    def test_action_routes_to_vote(self, mock_vote_service, client):
        """POST /action with button payload calls vote_service.vote."""
        response = client.post('/action', data={
            'payload': json.dumps(SAMPLE_PAYLOAD)
        })
        assert response.status_code == 200
        mock_vote_service.vote.assert_called_once()
        # Verify the payload was passed through
        call_payload = mock_vote_service.vote.call_args[0][0]
        assert call_payload['actions'][0]['value'] == '42'

    @patch('lunchbot.blueprints.slack_actions.vote_service')
    def test_action_non_button_skips_vote(self, mock_vote_service, client):
        """POST /action with non-button action does not call vote_service."""
        payload = dict(SAMPLE_PAYLOAD)
        payload['actions'] = [{'type': 'external_select', 'value': 'search'}]
        response = client.post('/action', data={
            'payload': json.dumps(payload)
        })
        assert response.status_code == 200
        mock_vote_service.vote.assert_not_called()
