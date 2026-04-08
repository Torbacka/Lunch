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
        'cuisine': 'Italian',
        'walking_minutes': 5,
        'pick_type': 'smart',
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
        'cuisine': 'Japanese',
        'walking_minutes': 12,
        'pick_type': 'random',
        'votes': [],
    },
]


class TestBuildPollBlocks:
    """Tests for build_poll_blocks()."""

    def test_header_block_present(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            assert blocks[0]['type'] == 'header'
            assert 'Lunch Poll' in blocks[0]['text']['text']

    def test_subtitle_section(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            assert blocks[1]['type'] == 'section'
            assert 'Where should we eat today' in blocks[1]['text']['text']

    def test_divider_after_header(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            assert blocks[2]['type'] == 'divider'

    def test_option_section_has_primary_vote_button(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            # First option section is at index 3
            option_section = blocks[3]
            assert option_section['type'] == 'section'
            assert 'Pasta Palace' in option_section['text']['text']
            assert option_section['accessory']['type'] == 'button'
            assert option_section['accessory']['value'] == '1'
            assert option_section['accessory']['style'] == 'primary'

    def test_cuisine_in_option_text(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            text = blocks[3]['text']['text']
            assert 'Italian' in text

    def test_walking_minutes_in_option_text(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            text = blocks[3]['text']['text']
            assert '5 min' in text

    def test_smart_badge_in_option_text(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            text = blocks[3]['text']['text']
            assert '`Smart`' in text

    def test_wild_badge_for_random_pick(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            # Second option starts at index 7 (3 header + 4 per first option)
            second_option = blocks[7]
            text = second_option['text']['text']
            assert '`Wild`' in text

    def test_vote_count_context(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            # Vote context block for first option (index 4)
            vote_ctx = blocks[4]
            assert vote_ctx['type'] == 'context'
            assert '2 votes' in vote_ctx['elements'][0]['text']

    def test_no_votes_shows_no_votes_yet(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            # Second option vote context at index 8
            vote_ctx = blocks[8]
            assert vote_ctx['type'] == 'context'
            assert 'No votes yet' in vote_ctx['elements'][0]['text']

    def test_single_vote_singular(self, app):
        """1 vote should say 'vote' not 'votes'."""
        options = [{
            'id': 3, 'name': 'Burger Bar', 'rating': 3.8, 'emoji': 'hamburger',
            'url': '', 'votes': ['U_CAROL'], 'pick_type': 'random',
        }]
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(options)
            vote_ctx = blocks[4]
            assert '1 vote' in vote_ctx['elements'][0]['text']
            assert '1 votes' not in vote_ctx['elements'][0]['text']

    def test_url_context_block(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            url_ctx = blocks[5]
            assert url_ctx['type'] == 'context'
            assert url_ctx['elements'][0]['type'] == 'mrkdwn'
            assert '<https://pastapalace.com|' in url_ctx['elements'][0]['text']

    def test_divider_after_each_option(self, app):
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            # Divider at index 6 (after first option) and 10 (after second option)
            assert blocks[6]['type'] == 'divider'
            assert blocks[10]['type'] == 'divider'

    def test_fallback_emoji_for_none(self, app):
        """When emoji is None, use fork_and_knife."""
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            # Second option section at index 7
            second_section = blocks[7]
            assert ':fork_and_knife:' in second_section['text']['text']

    def test_footer_total_votes(self, app):
        """Footer should show total vote count."""
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(SAMPLE_OPTIONS)
            footer = blocks[-1]
            assert footer['type'] == 'context'
            assert '2 votes' in footer['elements'][0]['text']

    def test_footer_zero_votes(self, app):
        """Footer should show 0 votes when nobody voted."""
        options = [{
            'id': 1, 'name': 'Test', 'rating': 4.0, 'emoji': 'pizza',
            'url': '', 'votes': [], 'pick_type': 'random',
        }]
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(options)
            footer = blocks[-1]
            assert '0 votes' in footer['elements'][0]['text']

    def test_no_cuisine_omitted(self, app):
        """When cuisine is None, it should not appear in the line."""
        options = [{
            'id': 1, 'name': 'Mystery Place', 'rating': 4.0, 'emoji': 'fork_and_knife',
            'url': '', 'votes': [], 'pick_type': 'smart', 'cuisine': None,
        }]
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(options)
            text = blocks[3]['text']['text']
            assert '\u00b7' not in text  # no separator when no cuisine

    def test_no_walking_minutes_omitted(self, app):
        """When walking_minutes is None, it should not appear in the line."""
        options = [{
            'id': 1, 'name': 'Far Away', 'rating': 4.0, 'emoji': 'pizza',
            'url': '', 'votes': [], 'pick_type': 'random',
            'walking_minutes': None, 'cuisine': 'Pizza',
        }]
        with app.app_context():
            from lunchbot.services.poll_service import build_poll_blocks
            blocks = build_poll_blocks(options)
            text = blocks[3]['text']['text']
            assert 'min' not in text


class TestClosePoll:
    """Tests for close_poll()."""

    def test_close_poll_with_winner(self, app):
        with app.app_context():
            with patch('lunchbot.services.poll_service.db_client') as mock_db, \
                 patch('lunchbot.services.poll_service.slack_client') as mock_slack:
                mock_db.get_poll_winner.return_value = {
                    'name': 'Pasta Palace',
                    'emoji': 'spaghetti',
                    'vote_count': 5,
                    'cuisine': 'Italian',
                    'walking_minutes': 5,
                    'url': 'https://maps.google.com/pasta',
                    'website': 'https://pastapalace.com',
                }
                mock_slack.post_message.return_value = {'ok': True}

                from lunchbot.services.poll_service import close_poll
                result = close_poll('#lunch', 'T_TEST')

                mock_slack.post_message.assert_called_once()
                blocks = mock_slack.post_message.call_args[0][1]
                # Header with trophy
                assert blocks[0]['type'] == 'header'
                assert 'winner' in blocks[0]['text']['text'].lower()
                # Winner name
                assert 'Pasta Palace' in blocks[1]['text']['text']
                assert '5 votes' in blocks[1]['text']['text']

    def test_close_poll_no_votes(self, app):
        with app.app_context():
            with patch('lunchbot.services.poll_service.db_client') as mock_db, \
                 patch('lunchbot.services.poll_service.slack_client') as mock_slack:
                mock_db.get_poll_winner.return_value = None
                mock_slack.post_message.return_value = {'ok': True}

                from lunchbot.services.poll_service import close_poll
                close_poll('#lunch', 'T_TEST')

                blocks = mock_slack.post_message.call_args[0][1]
                assert 'No votes' in blocks[0]['text']['text']


class TestPushPoll:
    """Tests for push_poll()."""

    def test_push_poll_calls_db_and_slack(self, app):
        with app.app_context():
            with patch('lunchbot.services.poll_service.ensure_poll_options'), \
                 patch('lunchbot.services.poll_service.db_client') as mock_db, \
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

    def test_returns_db_channel_when_set(self, app, clean_all_tables):
        """poll_channel_for returns workspace DB channel when configured."""
        app.config['SLACK_POLL_CHANNEL'] = '#fallback'
        with app.app_context():
            from lunchbot.client.workspace_client import save_workspace, update_workspace_settings
            from lunchbot.services.poll_service import poll_channel_for
            save_workspace('T_CHAN', 'Channel Team', 'enc_token', 'U_BOT', 'chat:write')
            update_workspace_settings('T_CHAN', poll_channel='#db-channel')
            assert poll_channel_for('T_CHAN') == '#db-channel'

    def test_falls_back_to_config_when_no_db_channel(self, app, clean_all_tables):
        """poll_channel_for falls back to config when workspace has no channel."""
        app.config['SLACK_POLL_CHANNEL'] = '#config-channel'
        with app.app_context():
            from lunchbot.client.workspace_client import save_workspace
            from lunchbot.services.poll_service import poll_channel_for
            save_workspace('T_NOCHA', 'No Channel Team', 'enc_token', 'U_BOT', 'chat:write')
            assert poll_channel_for('T_NOCHA') == '#config-channel'

    def test_falls_back_to_config_when_workspace_not_found(self, app, clean_all_tables):
        """poll_channel_for falls back to config when workspace doesn't exist."""
        app.config['SLACK_POLL_CHANNEL'] = '#config-fallback'
        with app.app_context():
            from lunchbot.services.poll_service import poll_channel_for
            assert poll_channel_for('T_MISSING') == '#config-fallback'

    def test_returns_empty_when_nothing_configured(self, app, clean_all_tables):
        app.config.pop('SLACK_POLL_CHANNEL', None)
        with app.app_context():
            from lunchbot.services.poll_service import poll_channel_for
            assert poll_channel_for('T_MISSING') == ''
