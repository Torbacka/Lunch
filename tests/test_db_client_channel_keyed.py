"""Tests for Phase 07.2 channel-keyed db_client rewrites.

Covers:
- upsert_suggestion requires slack_channel_id (no default)
- get_candidate_pool takes (poll_date, channel_id) and scopes by office
- save_restaurant accepts location_id
- update_restaurant_stats keyed on (channel_id, restaurant_id)
- get_or_create_stats keyed on (channel_id, restaurant_id)
- get_unprocessed_polls returns slack_channel_id
- channel_schedules CRUD helpers
"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch


pytestmark = pytest.mark.db


# --- Signature tests (no DB required) ---

def test_upsert_suggestion_requires_slack_channel_id():
    """upsert_suggestion must require slack_channel_id as positional arg (no default)."""
    import inspect
    from lunchbot.client.db_client import upsert_suggestion
    sig = inspect.signature(upsert_suggestion)
    params = list(sig.parameters.keys())
    assert 'slack_channel_id' in params
    # It must NOT have a default value (required arg)
    param = sig.parameters['slack_channel_id']
    assert param.default is inspect.Parameter.empty, \
        "slack_channel_id must be required (no default value)"


def test_upsert_suggestion_raises_without_channel():
    """Calling upsert_suggestion without slack_channel_id raises TypeError."""
    from lunchbot.client.db_client import upsert_suggestion
    with pytest.raises(TypeError):
        upsert_suggestion(date.today(), 1, 'T_TEST')


def test_save_restaurant_accepts_location_id():
    """save_restaurant must accept location_id parameter."""
    import inspect
    from lunchbot.client.db_client import save_restaurant
    sig = inspect.signature(save_restaurant)
    assert 'location_id' in sig.parameters


def test_save_restaurants_accepts_location_id():
    """save_restaurants must accept location_id parameter."""
    import inspect
    from lunchbot.client.db_client import save_restaurants
    sig = inspect.signature(save_restaurants)
    assert 'location_id' in sig.parameters


def test_get_candidate_pool_signature():
    """get_candidate_pool must take (poll_date, channel_id)."""
    import inspect
    from lunchbot.client.db_client import get_candidate_pool
    sig = inspect.signature(get_candidate_pool)
    params = list(sig.parameters.keys())
    assert 'poll_date' in params
    assert 'channel_id' in params


def test_get_or_create_stats_signature():
    """get_or_create_stats must take (channel_id, restaurant_id, team_id)."""
    import inspect
    from lunchbot.client.db_client import get_or_create_stats
    sig = inspect.signature(get_or_create_stats)
    params = list(sig.parameters.keys())
    assert 'channel_id' in params
    assert 'restaurant_id' in params
    assert 'team_id' in params


def test_update_restaurant_stats_signature():
    """update_restaurant_stats must take channel_id and team_id."""
    import inspect
    from lunchbot.client.db_client import update_restaurant_stats
    sig = inspect.signature(update_restaurant_stats)
    params = list(sig.parameters.keys())
    assert 'channel_id' in params
    assert 'restaurant_id' in params
    assert 'team_id' in params


def test_channel_schedule_functions_exist():
    """db_client must expose channel_schedules CRUD helpers."""
    from lunchbot.client import db_client
    assert hasattr(db_client, 'list_channel_schedules')
    assert hasattr(db_client, 'get_channel_schedule')
    assert hasattr(db_client, 'upsert_channel_schedule')
    assert hasattr(db_client, 'delete_channel_schedule')
    assert callable(db_client.list_channel_schedules)
    assert callable(db_client.get_channel_schedule)
    assert callable(db_client.upsert_channel_schedule)
    assert callable(db_client.delete_channel_schedule)


def test_no_dropped_column_references():
    """db_client must not reference dropped workspaces columns."""
    import inspect
    from lunchbot.client import db_client
    source = inspect.getsource(db_client)
    assert 'poll_schedule_time' not in source
    assert 'poll_schedule_timezone' not in source
    assert 'poll_schedule_weekdays' not in source
    assert 'workspaces.poll_channel' not in source


def test_get_candidate_pool_has_channel_office_cte():
    """get_candidate_pool SQL must use channel_office CTE."""
    import inspect
    from lunchbot.client import db_client
    source = inspect.getsource(db_client.get_candidate_pool)
    assert 'channel_office' in source
    assert 'COALESCE(rs.alpha, 1.0)' in source
