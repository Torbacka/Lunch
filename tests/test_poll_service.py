"""Tests for the poll builder service."""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock


SAMPLE_OPTIONS = [
    {
        'id': 1,
        'restaurant_id': 10,
        'place_id': 'ChIJ_abc',
        'name': 'Pasta Palace',
        'rating': 4.5,
        'emoji': 'spaghetti',
        'url': 'https://maps.google.com/pasta',
        'website': 'https://pastapalace.com',
        'price_level': 2,
        'votes': ['U_ALICE', 'U_BOB'],
    },
    {
        'id': 2,
        'restaurant_id': 20,
        'place_id': 'ChIJ_def',
        'name': 'Sushi Spot',
        'rating': 4.2,
        'emoji': None,
        'url': 'https://maps.google.com/sushi',
        'website': None,
        'price_level': 3,
        'votes': [],
    },
]


class TestBuildPollBlocks:
    """Tests for build_poll_blocks()."""

    def test_header_block_present(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            # First block is the header section
            assert blocks[0]['type'] == 'section'
            assert 'Where should we eat today' in blocks[0]['text']['text']

    def test_divider_after_header(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            assert blocks[1]['type'] == 'divider'

    def test_four_blocks_per_option(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            # header + divider + (4 blocks * 2 options) = 10
            assert len(blocks) == 10

    def test_option_section_has_vote_button(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            # First option section is at index 2
            option_section = blocks[2]
            assert option_section['type'] == 'section'
            assert 'Pasta Palace' in option_section['text']['text']
            assert option_section['accessory']['type'] == 'button'
            assert option_section['accessory']['value'] == '1'

    def test_vote_count_context(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            # Vote context block for first option (index 3)
            vote_ctx = blocks[3]
            assert vote_ctx['type'] == 'context'
            assert '2 votes' in vote_ctx['elements'][0]['text']

    def test_no_votes_shows_no_votes(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            # Second option vote context at index 7 (2 + 4*1 + 1)
            vote_ctx = blocks[7]
            assert vote_ctx['type'] == 'context'
            assert 'No votes' in vote_ctx['elements'][0]['text']

    def test_single_vote_singular(self, app):
        """1 vote should say 'vote' not 'votes'."""
        options = [{
            'id': 3, 'name': 'Burger Bar', 'rating': 3.8, 'emoji': 'hamburger',
            'url': '', 'votes': ['U_CAROL'],
        }]
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(options)
            vote_ctx = blocks[3]
            assert '1 vote' in vote_ctx['elements'][0]['text']
            assert '1 votes' not in vote_ctx['elements'][0]['text']

    def test_url_context_block(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            url_ctx = blocks[4]
            assert url_ctx['type'] == 'context'
            assert url_ctx['elements'][0]['type'] == 'mrkdwn'
            # URL context now renders as markdown link: <url|More info>
            # Should prefer website over url
            assert '<https://pastapalace.com|More info>' in url_ctx['elements'][0]['text']

    def test_divider_after_each_option(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            # Divider at index 5 (after first option) and 9 (after second option)
            assert blocks[5]['type'] == 'divider'
            assert blocks[9]['type'] == 'divider'

    def test_fallback_emoji_for_none(self, app):
        """When emoji is None, use knife_fork_plate."""
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            # Second option section at index 6
            second_section = blocks[6]
            assert ':knife_fork_plate:' in second_section['text']['text']


class TestPushPoll:
    """Tests for push_poll()."""

    def test_push_poll_calls_db_and_slack(self, app):
        with app.app_context():
            with patch('lunchbot.services.poll_service.db_client') as mock_db, \
                 patch('lunchbot.services.poll_service.slack_client') as mock_slack:
                mock_db.get_votes.return_value = SAMPLE_OPTIONS
                mock_slack.post_message.return_value = {'ok': True, 'ts': '111.222'}

                from lunchbot.services.poll_service import push_poll
                result = push_poll('#lunch', 'T_TEST')

                mock_db.get_votes.assert_called_once_with(date.today())
                mock_slack.post_message.assert_called_once()
                call_args = mock_slack.post_message.call_args
                assert call_args[0][0] == '#lunch'
                assert call_args[0][2] == 'T_TEST'
                assert result == {'ok': True, 'ts': '111.222'}


class TestPollChannelFor:
    """Tests for poll_channel_for()."""

    def test_returns_config_channel(self, app):
        app.config['SLACK_POLL_CHANNEL'] = '#lunch-votes'
        with app.app_context():
            from lunchbot.services.poll_service import poll_channel_for
            assert poll_channel_for('T_TEST') == '#lunch-votes'

    def test_returns_empty_when_not_configured(self, app):
        app.config.pop('SLACK_POLL_CHANNEL', None)
        with app.app_context():
            from lunchbot.services.poll_service import poll_channel_for
            assert poll_channel_for('T_TEST') == ''
