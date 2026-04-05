"""Integration tests for restaurant_stats DB operations.

Tests for BOT-11 (reputation tracking, stats CRUD, candidate pool).
All tests require running PostgreSQL with migration 003 applied.
"""
import pytest
from datetime import date, timedelta
from lunchbot.client import db_client


def _insert_workspace(conn, team_id='T_TEST', team_name='Test Team'):
    """Insert a workspace and return its team_id."""
    conn.execute(
        """INSERT INTO workspaces (team_id, team_name, bot_token_encrypted)
           VALUES (%s, %s, 'test_token_enc') ON CONFLICT DO NOTHING""",
        (team_id, team_name)
    )
    return team_id


def _insert_restaurant(conn, workspace_id, place_id='place_1', name='Test Restaurant'):
    """Insert a restaurant and return its id."""
    from psycopg.rows import dict_row
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """INSERT INTO restaurants (place_id, name, workspace_id)
               VALUES (%s, %s, %s)
               ON CONFLICT (place_id) DO UPDATE SET name = EXCLUDED.name
               RETURNING id""",
            (place_id, name, workspace_id)
        )
        return cur.fetchone()['id']


def _insert_poll(conn, workspace_id, poll_date=None):
    """Insert a poll and return its id."""
    from psycopg.rows import dict_row
    poll_date = poll_date or date.today()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """INSERT INTO polls (poll_date, workspace_id)
               VALUES (%s, %s)
               ON CONFLICT (poll_date, workspace_id) DO UPDATE SET poll_date = EXCLUDED.poll_date
               RETURNING id""",
            (poll_date, workspace_id)
        )
        return cur.fetchone()['id']


def _insert_poll_option(conn, poll_id, restaurant_id, workspace_id, display_order=0):
    """Insert a poll option and return its id."""
    from psycopg.rows import dict_row
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """INSERT INTO poll_options (poll_id, restaurant_id, display_order, workspace_id)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (poll_id, restaurant_id) DO NOTHING
               RETURNING id""",
            (poll_id, restaurant_id, display_order, workspace_id)
        )
        row = cur.fetchone()
        return row['id'] if row else None


def _insert_vote(conn, poll_option_id, user_id, workspace_id):
    """Insert a vote."""
    conn.execute(
        "INSERT INTO votes (poll_option_id, user_id, workspace_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        (poll_option_id, user_id, workspace_id)
    )


def test_get_or_create_stats_creates_default(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """BOT-11: New restaurant gets default alpha=1.0, beta=1.0, times_shown=0."""
    workspace_id = workspace_a['team_id']
    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        restaurant_id = _insert_restaurant(conn, workspace_id)

    stats = db_client.get_or_create_stats(restaurant_id, workspace_id=workspace_id)
    assert stats is not None
    assert float(stats['alpha']) == 1.0
    assert float(stats['beta']) == 1.0
    assert stats['times_shown'] == 0
    assert stats['restaurant_id'] == restaurant_id


def test_get_or_create_stats_returns_existing(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """BOT-11: Existing stats row is returned unchanged."""
    workspace_id = workspace_a['team_id']
    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        restaurant_id = _insert_restaurant(conn, workspace_id)
        # Insert custom stats row
        conn.execute(
            """INSERT INTO restaurant_stats (restaurant_id, workspace_id, alpha, beta, times_shown)
               VALUES (%s, %s, 5.0, 3.0, 2)""",
            (restaurant_id, workspace_id)
        )

    stats = db_client.get_or_create_stats(restaurant_id, workspace_id=workspace_id)
    assert stats is not None
    assert float(stats['alpha']) == 5.0
    assert float(stats['beta']) == 3.0
    assert stats['times_shown'] == 2


def test_get_candidate_pool_excludes_today(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """D-15: Candidate pool excludes restaurants already in today's poll."""
    workspace_id = workspace_a['team_id']
    today = date.today()

    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        # Two restaurants; one in today's poll, one not
        r1 = _insert_restaurant(conn, workspace_id, place_id='place_in_poll', name='In Poll')
        r2 = _insert_restaurant(conn, workspace_id, place_id='place_candidate', name='Candidate')

        poll_id = _insert_poll(conn, workspace_id, poll_date=today)
        _insert_poll_option(conn, poll_id, r1, workspace_id)

    pool = db_client.get_candidate_pool(today)
    pool_ids = [r['restaurant_id'] for r in pool]
    assert r1 not in pool_ids   # already in poll
    assert r2 in pool_ids       # should be a candidate


def test_update_stats_from_poll_increments_alpha_beta(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """D-06: update_restaurant_stats correctly increments alpha and beta from vote data."""
    workspace_id = workspace_a['team_id']

    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        restaurant_id = _insert_restaurant(conn, workspace_id)

    # First call: creates row with base + increment (1.0 + 2, 1.0 + 1)
    db_client.update_restaurant_stats(restaurant_id, alpha_increment=2, beta_increment=1, workspace_id=workspace_id)
    stats = db_client.get_or_create_stats(restaurant_id, workspace_id=workspace_id)
    assert float(stats['alpha']) == 3.0   # 1.0 (base) + 2
    assert float(stats['beta']) == 2.0    # 1.0 (base) + 1
    assert stats['times_shown'] == 1

    # Second call: increments existing row
    db_client.update_restaurant_stats(restaurant_id, alpha_increment=1, beta_increment=2, workspace_id=workspace_id)
    stats = db_client.get_or_create_stats(restaurant_id, workspace_id=workspace_id)
    assert float(stats['alpha']) == 4.0   # 3.0 + 1
    assert float(stats['beta']) == 4.0    # 2.0 + 2
    assert stats['times_shown'] == 2


def test_update_stats_idempotent(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """A3: Re-processing a marked poll is a no-op because get_unprocessed_polls skips it."""
    workspace_id = workspace_a['team_id']
    yesterday = date.today() - timedelta(days=1)

    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        restaurant_id = _insert_restaurant(conn, workspace_id)
        poll_id = _insert_poll(conn, workspace_id, poll_date=yesterday)
        opt_id = _insert_poll_option(conn, poll_id, restaurant_id, workspace_id)
        _insert_vote(conn, opt_id, 'user_1', workspace_id)

    # First processing pass — should find unprocessed poll
    unprocessed = db_client.get_unprocessed_polls(date.today())
    assert len(unprocessed) >= 1

    # Mark processed
    db_client.mark_poll_stats_processed(poll_id)

    # Second pass — poll should now be excluded
    unprocessed_after = db_client.get_unprocessed_polls(date.today())
    ids_after = [p['id'] for p in unprocessed_after]
    assert poll_id not in ids_after


def test_get_candidate_pool_uses_coalesce_defaults(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """D-07: Restaurants with no stats row get alpha=1.0, beta=1.0 from COALESCE."""
    workspace_id = workspace_a['team_id']
    today = date.today()

    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        _insert_restaurant(conn, workspace_id, place_id='place_no_stats', name='No Stats')

    pool = db_client.get_candidate_pool(today)
    assert len(pool) >= 1
    # Restaurant with no stats row should have defaults
    r = next((r for r in pool if r['name'] == 'No Stats'), None)
    assert r is not None
    assert float(r['alpha']) == 1.0
    assert float(r['beta']) == 1.0
    assert r['times_shown'] == 0
