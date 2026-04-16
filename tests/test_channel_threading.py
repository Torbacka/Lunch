"""Tests for channel_id threading through poll-build and stats-write paths.

Phase 07.2 Plan 05: ensure_poll_options, update_stats_lazy, and push_poll
all thread channel_id to db_client calls.
"""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock, call


class TestEnsurePollOptionsChannelThreading:
    """ensure_poll_options must pass channel_id to db_client calls."""

    def test_signature_accepts_channel_id(self, app):
        """ensure_poll_options accepts channel_id as a required parameter."""
        from lunchbot.services.recommendation_service import ensure_poll_options
        import inspect
        sig = inspect.signature(ensure_poll_options)
        assert 'channel_id' in sig.parameters

    def test_get_candidate_pool_receives_channel_id(self, app):
        """get_candidate_pool is called with (poll_date, channel_id)."""
        with app.app_context():
            with patch('lunchbot.services.recommendation_service.db_client') as mock_db, \
                 patch('lunchbot.services.recommendation_service.update_stats_lazy'), \
                 patch('lunchbot.services.recommendation_service.get_workspace_settings', return_value={'poll_size': 4, 'smart_picks': 2}):
                mock_db.get_votes.return_value = []
                mock_db.get_candidate_pool.return_value = []

                from lunchbot.services.recommendation_service import ensure_poll_options
                ensure_poll_options(
                    poll_date=date(2025, 1, 15),
                    workspace_id='T_TEST',
                    channel_id='C_LUNCH',
                )

                mock_db.get_candidate_pool.assert_called_once_with(
                    date(2025, 1, 15), 'C_LUNCH'
                )

    def test_upsert_suggestion_receives_channel_id(self, app):
        """upsert_suggestion is called with channel_id for each pick."""
        with app.app_context():
            with patch('lunchbot.services.recommendation_service.db_client') as mock_db, \
                 patch('lunchbot.services.recommendation_service.update_stats_lazy'), \
                 patch('lunchbot.services.recommendation_service.get_workspace_settings', return_value={'poll_size': 4, 'smart_picks': 2}):
                mock_db.get_votes.return_value = []
                mock_db.get_candidate_pool.return_value = [
                    {'restaurant_id': 1, 'alpha': 5.0, 'beta': 1.0, 'name': 'A', 'types': None, 'geometry': None},
                    {'restaurant_id': 2, 'alpha': 1.0, 'beta': 5.0, 'name': 'B', 'types': None, 'geometry': None},
                    {'restaurant_id': 3, 'alpha': 3.0, 'beta': 2.0, 'name': 'C', 'types': None, 'geometry': None},
                    {'restaurant_id': 4, 'alpha': 2.0, 'beta': 3.0, 'name': 'D', 'types': None, 'geometry': None},
                ]

                from lunchbot.services.recommendation_service import ensure_poll_options
                ensure_poll_options(
                    poll_date=date(2025, 1, 15),
                    workspace_id='T_TEST',
                    channel_id='C_LUNCH',
                )

                # Every upsert_suggestion call must include channel_id='C_LUNCH'
                for c in mock_db.upsert_suggestion.call_args_list:
                    # positional: poll_date, restaurant_id, workspace_id, channel_id
                    assert len(c.args) >= 4 or 'channel_id' in c.kwargs
                    if len(c.args) >= 4:
                        assert c.args[3] == 'C_LUNCH'
                    else:
                        assert c.kwargs['channel_id'] == 'C_LUNCH'


class TestUpdateStatsLazyChannelThreading:
    """update_stats_lazy must read channel_id from poll rows and pass to update_restaurant_stats."""

    def test_reads_channel_id_from_poll(self, app):
        """update_stats_lazy reads slack_channel_id from each poll and passes to update_restaurant_stats."""
        with app.app_context():
            with patch('lunchbot.services.recommendation_service.db_client') as mock_db:
                mock_db.get_unprocessed_polls.return_value = [
                    {'id': 1, 'poll_date': date(2025, 1, 14), 'workspace_id': 'T_TEST', 'slack_channel_id': 'C_LUNCH'},
                ]
                mock_db.get_poll_vote_shares.return_value = [
                    {'restaurant_id': 10, 'votes_received': 3, 'total_unique_voters': 5},
                ]

                from lunchbot.services.recommendation_service import update_stats_lazy
                update_stats_lazy(today=date(2025, 1, 15))

                mock_db.update_restaurant_stats.assert_called_once()
                call_args = mock_db.update_restaurant_stats.call_args
                # channel_id must be the first positional arg
                assert call_args.args[0] == 'C_LUNCH'

    def test_null_channel_skipped_with_warning(self, app):
        """Polls with NULL slack_channel_id are skipped and marked processed."""
        with app.app_context():
            with patch('lunchbot.services.recommendation_service.db_client') as mock_db, \
                 patch('lunchbot.services.recommendation_service.logger') as mock_logger:
                mock_db.get_unprocessed_polls.return_value = [
                    {'id': 2, 'poll_date': date(2025, 1, 14), 'workspace_id': 'T_TEST', 'slack_channel_id': None},
                ]

                from lunchbot.services.recommendation_service import update_stats_lazy
                update_stats_lazy(today=date(2025, 1, 15))

                # Should NOT call get_poll_vote_shares for skipped poll
                mock_db.get_poll_vote_shares.assert_not_called()
                # Should still mark as processed
                mock_db.mark_poll_stats_processed.assert_called_once_with(2)
                # Should log warning
                mock_logger.warning.assert_called_once()
                assert 'slack_channel_id' in mock_logger.warning.call_args.args[0]

    def test_workspace_id_passed_to_update_restaurant_stats(self, app):
        """update_restaurant_stats receives workspace_id from poll row."""
        with app.app_context():
            with patch('lunchbot.services.recommendation_service.db_client') as mock_db:
                mock_db.get_unprocessed_polls.return_value = [
                    {'id': 1, 'poll_date': date(2025, 1, 14), 'workspace_id': 'T_ALPHA', 'slack_channel_id': 'C_LUNCH'},
                ]
                mock_db.get_poll_vote_shares.return_value = [
                    {'restaurant_id': 10, 'votes_received': 2, 'total_unique_voters': 4},
                ]

                from lunchbot.services.recommendation_service import update_stats_lazy
                update_stats_lazy(today=date(2025, 1, 15))

                call_args = mock_db.update_restaurant_stats.call_args
                # workspace_id should be passed (last positional or keyword)
                assert 'T_ALPHA' in call_args.args or call_args.kwargs.get('workspace_id') == 'T_ALPHA'


class TestPushPollChannelThreading:
    """push_poll must pass channel_id to ensure_poll_options."""

    def test_push_poll_passes_channel_id(self, app):
        """push_poll passes channel as channel_id to ensure_poll_options."""
        with app.app_context():
            with patch('lunchbot.services.poll_service.ensure_poll_options') as mock_ensure, \
                 patch('lunchbot.services.poll_service.db_client') as mock_db, \
                 patch('lunchbot.services.poll_service.slack_client') as mock_slack:
                mock_ensure.return_value = 0
                mock_db.get_votes.return_value = []
                mock_slack.post_message.return_value = {'ok': True}

                from lunchbot.services.poll_service import push_poll
                push_poll('#lunch', 'T_TEST')

                mock_ensure.assert_called_once()
                call_kwargs = mock_ensure.call_args.kwargs
                assert call_kwargs.get('channel_id') == '#lunch'
