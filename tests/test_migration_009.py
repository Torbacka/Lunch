"""Smoke tests for migration 009: office-scoped candidates + channel schedules.

Asserts post-upgrade schema invariants. Assumes alembic upgrade head has been
run by the global pytest fixture (test DB is fully migrated).
"""
import pytest


pytestmark = pytest.mark.db


def _query_columns(conn, table_name):
    """Return dict of column_name -> is_nullable for a table."""
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
    """, (table_name,))
    return {row[0]: row[1] for row in cur.fetchall()}


def _query_pk_columns(conn, table_name):
    """Return sorted list of PK column names for a table."""
    cur = conn.cursor()
    cur.execute("""
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = 'public'
          AND tc.table_name = %s
          AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY kcu.ordinal_position
    """, (table_name,))
    return [row[0] for row in cur.fetchall()]


def test_restaurants_location_id_not_null(app_context, app):
    """Migration 009: restaurants.location_id is NOT NULL."""
    pool = app.extensions['pool']
    with pool.connection() as conn:
        cols = _query_columns(conn, 'restaurants')
    assert 'location_id' in cols, "restaurants.location_id column missing"
    assert cols['location_id'] == 'NO', "restaurants.location_id should be NOT NULL"


def test_restaurant_stats_primary_key(app_context, app):
    """Migration 009: restaurant_stats PK is (channel_id, restaurant_id), no workspace_id column."""
    pool = app.extensions['pool']
    with pool.connection() as conn:
        pk_cols = _query_pk_columns(conn, 'restaurant_stats')
        cols = _query_columns(conn, 'restaurant_stats')

    assert pk_cols == ['channel_id', 'restaurant_id'], \
        f"Expected PK (channel_id, restaurant_id), got {pk_cols}"
    assert 'workspace_id' not in cols, \
        "restaurant_stats should not have workspace_id column after migration 009"


def test_polls_slack_channel_id_not_null(app_context, app):
    """Migration 009: polls.slack_channel_id is NOT NULL."""
    pool = app.extensions['pool']
    with pool.connection() as conn:
        cols = _query_columns(conn, 'polls')
    assert 'slack_channel_id' in cols, "polls.slack_channel_id column missing"
    assert cols['slack_channel_id'] == 'NO', "polls.slack_channel_id should be NOT NULL"


def test_channel_schedules_exists(app_context, app):
    """Migration 009: channel_schedules table exists with PK (team_id, channel_id)."""
    pool = app.extensions['pool']
    with pool.connection() as conn:
        # Should not raise
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM channel_schedules LIMIT 0")

        pk_cols = _query_pk_columns(conn, 'channel_schedules')
    assert pk_cols == ['team_id', 'channel_id'], \
        f"Expected PK (team_id, channel_id), got {pk_cols}"


def test_workspaces_schedule_columns_dropped(app_context, app):
    """Migration 009: legacy schedule columns removed from workspaces."""
    pool = app.extensions['pool']
    with pool.connection() as conn:
        cols = _query_columns(conn, 'workspaces')

    dropped = ['poll_schedule_time', 'poll_schedule_timezone',
               'poll_schedule_weekdays', 'poll_channel']
    for col in dropped:
        assert col not in cols, f"workspaces.{col} should have been dropped by migration 009"
