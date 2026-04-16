"""Integration tests for restaurant_stats DB operations.

Tests for BOT-11 (reputation tracking, stats CRUD, candidate pool).
Phase 07.2: G-01 office isolation, G-02 per-channel divergence, cascade, Beta fallback.
All tests require running PostgreSQL with migration 009 applied.
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


def _insert_workspace_location(conn, team_id, name='Main', lat_lng=None, is_default=True):
    """Insert a workspace_location (office) and return its id."""
    lat_lng = lat_lng or {'lat': 59.0, 'lng': 18.0}
    lat_lng_str = f"{lat_lng['lat']},{lat_lng['lng']}"
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO workspace_locations (team_id, name, lat_lng, is_default) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (team_id, name, lat_lng_str, is_default),
    )
    return cur.fetchone()[0]


def _insert_channel_location(conn, team_id, channel_id, location_id):
    """Bind a channel to a workspace_location (office)."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO channel_locations (team_id, channel_id, location_id) VALUES (%s, %s, %s)",
        (team_id, channel_id, location_id),
    )


def _insert_restaurant(conn, workspace_id, location_id, place_id='place_1', name='Test Restaurant', rating=4.0):
    """Insert a restaurant tagged to a location and return its id."""
    from psycopg.rows import dict_row
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """INSERT INTO restaurants (place_id, name, workspace_id, rating, location_id)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (place_id) DO UPDATE SET name = EXCLUDED.name, rating = EXCLUDED.rating
               RETURNING id""",
            (place_id, name, workspace_id, rating, location_id)
        )
        return cur.fetchone()['id']


def _insert_poll(conn, workspace_id, slack_channel_id, poll_date=None):
    """Insert a poll and return its id."""
    from psycopg.rows import dict_row
    poll_date = poll_date or date.today()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """INSERT INTO polls (poll_date, workspace_id, slack_channel_id)
               VALUES (%s, %s, %s)
               ON CONFLICT (poll_date, workspace_id) DO UPDATE SET poll_date = EXCLUDED.poll_date
               RETURNING id""",
            (poll_date, workspace_id, slack_channel_id)
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


# ---------------------------------------------------------------------------
# Existing tests updated for per-channel schema (migration 009)
# ---------------------------------------------------------------------------

def test_get_or_create_stats_creates_default(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """BOT-11: New restaurant gets default alpha=1.0, beta=1.0, times_shown=0."""
    workspace_id = workspace_a['team_id']
    channel_id = 'C_STATS'
    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        loc_id = _insert_workspace_location(conn, workspace_id)
        restaurant_id = _insert_restaurant(conn, workspace_id, loc_id)

    stats = db_client.get_or_create_stats(channel_id, restaurant_id, team_id=workspace_id)
    assert stats is not None
    assert float(stats['alpha']) == 1.0
    assert float(stats['beta']) == 1.0
    assert stats['times_shown'] == 0
    assert stats['restaurant_id'] == restaurant_id


def test_get_or_create_stats_returns_existing(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """BOT-11: Existing stats row is returned unchanged."""
    workspace_id = workspace_a['team_id']
    channel_id = 'C_STATS'
    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        loc_id = _insert_workspace_location(conn, workspace_id)
        restaurant_id = _insert_restaurant(conn, workspace_id, loc_id)
        # Insert custom stats row
        conn.execute(
            """INSERT INTO restaurant_stats (channel_id, restaurant_id, team_id, alpha, beta, times_shown)
               VALUES (%s, %s, %s, 5.0, 3.0, 2)""",
            (channel_id, restaurant_id, workspace_id)
        )

    stats = db_client.get_or_create_stats(channel_id, restaurant_id, team_id=workspace_id)
    assert stats is not None
    assert float(stats['alpha']) == 5.0
    assert float(stats['beta']) == 3.0
    assert stats['times_shown'] == 2


def test_get_candidate_pool_excludes_today(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """D-15: Candidate pool excludes restaurants already in today's poll."""
    workspace_id = workspace_a['team_id']
    channel_id = 'C_POOL'
    today = date.today()

    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        loc_id = _insert_workspace_location(conn, workspace_id)
        _insert_channel_location(conn, workspace_id, channel_id, loc_id)
        # Two restaurants; one in today's poll, one not
        r1 = _insert_restaurant(conn, workspace_id, loc_id, place_id='place_in_poll', name='In Poll')
        r2 = _insert_restaurant(conn, workspace_id, loc_id, place_id='place_candidate', name='Candidate')

        poll_id = _insert_poll(conn, workspace_id, channel_id, poll_date=today)
        _insert_poll_option(conn, poll_id, r1, workspace_id)

    pool = db_client.get_candidate_pool(today, channel_id)
    pool_ids = [r['restaurant_id'] for r in pool]
    assert r1 not in pool_ids   # already in poll
    assert r2 in pool_ids       # should be a candidate


def test_update_stats_from_poll_increments_alpha_beta(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """D-06: update_restaurant_stats correctly increments alpha and beta from vote data."""
    workspace_id = workspace_a['team_id']
    channel_id = 'C_INC'

    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        loc_id = _insert_workspace_location(conn, workspace_id)
        restaurant_id = _insert_restaurant(conn, workspace_id, loc_id)

    # First call: creates row with base + increment (1.0 + 2, 1.0 + 1)
    db_client.update_restaurant_stats(channel_id, restaurant_id, alpha_increment=2, beta_increment=1, team_id=workspace_id)
    stats = db_client.get_or_create_stats(channel_id, restaurant_id, team_id=workspace_id)
    assert float(stats['alpha']) == 3.0   # 1.0 (base) + 2
    assert float(stats['beta']) == 2.0    # 1.0 (base) + 1
    assert stats['times_shown'] == 1

    # Second call: increments existing row
    db_client.update_restaurant_stats(channel_id, restaurant_id, alpha_increment=1, beta_increment=2, team_id=workspace_id)
    stats = db_client.get_or_create_stats(channel_id, restaurant_id, team_id=workspace_id)
    assert float(stats['alpha']) == 4.0   # 3.0 + 1
    assert float(stats['beta']) == 4.0    # 2.0 + 2
    assert stats['times_shown'] == 2


def test_update_stats_idempotent(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """A3: Re-processing a marked poll is a no-op because get_unprocessed_polls skips it."""
    workspace_id = workspace_a['team_id']
    channel_id = 'C_IDEMP'
    yesterday = date.today() - timedelta(days=1)

    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        loc_id = _insert_workspace_location(conn, workspace_id)
        restaurant_id = _insert_restaurant(conn, workspace_id, loc_id)
        poll_id = _insert_poll(conn, workspace_id, channel_id, poll_date=yesterday)
        opt_id = _insert_poll_option(conn, poll_id, restaurant_id, workspace_id)
        _insert_vote(conn, opt_id, 'user_1', workspace_id)

    # First processing pass -- should find unprocessed poll
    unprocessed = db_client.get_unprocessed_polls(date.today())
    assert len(unprocessed) >= 1

    # Mark processed
    db_client.mark_poll_stats_processed(poll_id)

    # Second pass -- poll should now be excluded
    unprocessed_after = db_client.get_unprocessed_polls(date.today())
    ids_after = [p['id'] for p in unprocessed_after]
    assert poll_id not in ids_after


def test_get_candidate_pool_uses_coalesce_defaults(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """D-07: Restaurants with no stats row get alpha=1.0, beta=1.0 from COALESCE."""
    workspace_id = workspace_a['team_id']
    channel_id = 'C_COALESCE'
    today = date.today()

    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        loc_id = _insert_workspace_location(conn, workspace_id)
        _insert_channel_location(conn, workspace_id, channel_id, loc_id)
        _insert_restaurant(conn, workspace_id, loc_id, place_id='place_no_stats', name='No Stats')

    pool = db_client.get_candidate_pool(today, channel_id)
    assert len(pool) >= 1
    # Restaurant with no stats row should have defaults
    r = next((r for r in pool if r['name'] == 'No Stats'), None)
    assert r is not None
    assert float(r['alpha']) == 1.0
    assert float(r['beta']) == 1.0
    assert r['times_shown'] == 0


# ---------------------------------------------------------------------------
# G-01 regression: office isolation (two channels, two offices, disjoint pools)
# ---------------------------------------------------------------------------

def test_get_candidate_pool_office_isolation(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """G-01: Two channels bound to different offices must have disjoint candidate pools."""
    workspace_id = workspace_a['team_id']
    today = date.today()

    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)

        # Office A
        loc_a = _insert_workspace_location(conn, workspace_id, name='Office A',
                                           lat_lng={'lat': 59.0, 'lng': 18.0}, is_default=True)
        # Office B
        loc_b = _insert_workspace_location(conn, workspace_id, name='Office B',
                                           lat_lng={'lat': 57.0, 'lng': 16.0}, is_default=False)

        # Bind channels to offices
        _insert_channel_location(conn, workspace_id, 'C_A', loc_a)
        _insert_channel_location(conn, workspace_id, 'C_B', loc_b)

        # 2 restaurants per office
        _insert_restaurant(conn, workspace_id, loc_a, place_id='pa_1', name='A Rest 1')
        _insert_restaurant(conn, workspace_id, loc_a, place_id='pa_2', name='A Rest 2')
        _insert_restaurant(conn, workspace_id, loc_b, place_id='pb_1', name='B Rest 1')
        _insert_restaurant(conn, workspace_id, loc_b, place_id='pb_2', name='B Rest 2')

    pool_a = db_client.get_candidate_pool(today, 'C_A')
    pool_b = db_client.get_candidate_pool(today, 'C_B')

    ids_a = set(r['restaurant_id'] for r in pool_a)
    ids_b = set(r['restaurant_id'] for r in pool_b)

    assert len(ids_a) == 2, f"Expected 2 restaurants in pool A, got {len(ids_a)}"
    assert len(ids_b) == 2, f"Expected 2 restaurants in pool B, got {len(ids_b)}"
    assert ids_a.isdisjoint(ids_b), "G-01 violated: pools overlap across offices"


# ---------------------------------------------------------------------------
# G-02 regression: per-channel stats divergence (same office, independent posteriors)
# ---------------------------------------------------------------------------

def test_restaurant_stats_divergence_same_office(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """G-02: Two channels in the same office accumulate divergent restaurant_stats rows."""
    workspace_id = workspace_a['team_id']

    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        loc_id = _insert_workspace_location(conn, workspace_id)
        _insert_channel_location(conn, workspace_id, 'C_1', loc_id)
        _insert_channel_location(conn, workspace_id, 'C_2', loc_id)
        r1 = _insert_restaurant(conn, workspace_id, loc_id, place_id='shared_r1', name='Shared')

    # Divergent updates: C_1 gets many votes (alpha), C_2 gets many non-votes (beta)
    db_client.update_restaurant_stats('C_1', r1, alpha_increment=5, beta_increment=0, team_id=workspace_id)
    db_client.update_restaurant_stats('C_2', r1, alpha_increment=0, beta_increment=5, team_id=workspace_id)

    row_c1 = db_client.get_or_create_stats('C_1', r1, team_id=workspace_id)
    row_c2 = db_client.get_or_create_stats('C_2', r1, team_id=workspace_id)

    assert float(row_c1['alpha']) > float(row_c2['alpha']), "G-02: C_1 alpha should be higher"
    assert float(row_c1['beta']) < float(row_c2['beta']), "G-02: C_1 beta should be lower"


# ---------------------------------------------------------------------------
# Beta(1,1) fallback for new channel
# ---------------------------------------------------------------------------

def test_get_candidate_pool_new_channel_prior(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """New channel with no stats rows falls back to Beta(1,1) uninformative prior."""
    workspace_id = workspace_a['team_id']
    today = date.today()

    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        loc_id = _insert_workspace_location(conn, workspace_id)
        _insert_channel_location(conn, workspace_id, 'C_NEW', loc_id)
        _insert_restaurant(conn, workspace_id, loc_id, place_id='place_new', name='New Place')

    pool = db_client.get_candidate_pool(today, 'C_NEW')
    assert len(pool) >= 1
    row = pool[0]
    assert float(row['alpha']) == 1.0
    assert float(row['beta']) == 1.0
    assert row['times_shown'] == 0


# ---------------------------------------------------------------------------
# Cascade: deleting office cascades to restaurants and stats
# ---------------------------------------------------------------------------

def test_delete_office_cascades_restaurants_and_stats(app_context, clean_all_tables_with_stats, tenant_connection, workspace_a):
    """D-05: DELETE FROM workspace_locations cascades to restaurants and restaurant_stats."""
    workspace_id = workspace_a['team_id']

    with tenant_connection(workspace_id) as conn:
        _insert_workspace(conn, workspace_id)
        loc_id = _insert_workspace_location(conn, workspace_id, name='Doomed Office')
        _insert_channel_location(conn, workspace_id, 'C_DOOM', loc_id)
        r_id = _insert_restaurant(conn, workspace_id, loc_id, place_id='doomed_r', name='Doomed')

    # Create a stats row via the public API
    db_client.update_restaurant_stats('C_DOOM', r_id, alpha_increment=1, beta_increment=1, team_id=workspace_id)

    # Verify the rows exist before delete
    with tenant_connection(workspace_id) as conn:
        from psycopg.rows import dict_row
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id FROM restaurants WHERE id = %s", (r_id,))
            assert cur.fetchone() is not None, "Restaurant should exist before delete"

        # Delete the office
        conn.execute("DELETE FROM workspace_locations WHERE id = %s", (loc_id,))

        # Assert restaurant gone
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id FROM restaurants WHERE id = %s", (r_id,))
            assert cur.fetchone() is None, "Restaurant should be cascaded"

            cur.execute("SELECT * FROM restaurant_stats WHERE restaurant_id = %s", (r_id,))
            assert cur.fetchone() is None, "Stats should be cascaded"
