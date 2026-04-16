"""Tests for PostgreSQL schema and db_client CRUD operations (INFRA-03)."""
import pytest
from datetime import date


pytestmark = pytest.mark.db


def _ensure_workspace_and_location(app):
    """Helper: insert workspace T_TEST and a default location, return location_id."""
    pool = app.extensions['pool']
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO workspaces (team_id, team_name, bot_token_encrypted) "
            "VALUES ('T_TEST', 'Test', 'enc') ON CONFLICT DO NOTHING"
        )
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO workspace_locations (team_id, name, latitude, longitude, is_default) "
            "VALUES ('T_TEST', 'HQ', 59.0, 18.0, TRUE) "
            "ON CONFLICT DO NOTHING RETURNING id"
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "SELECT id FROM workspace_locations WHERE team_id = 'T_TEST' LIMIT 1"
        )
        return cur.fetchone()[0]


def test_schema_tables_exist(app_context, app):
    """INFRA-03: All four normalized tables exist in PostgreSQL."""
    pool = app.extensions['pool']
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
    assert 'restaurants' in tables
    assert 'polls' in tables
    assert 'poll_options' in tables
    assert 'votes' in tables


def test_restaurant_upsert(app_context, clean_tables, sample_restaurant, app):
    """INFRA-03: Restaurant upsert creates and updates correctly."""
    from lunchbot.client.db_client import save_restaurant, get_restaurant_by_place_id

    loc_id = _ensure_workspace_and_location(app)
    restaurant_id = save_restaurant(sample_restaurant, location_id=loc_id, workspace_id='T_TEST')
    assert restaurant_id is not None
    assert isinstance(restaurant_id, int)

    # Verify retrieval
    fetched = get_restaurant_by_place_id('ChIJtest123')
    assert fetched is not None
    assert fetched['name'] == 'Test Restaurant'
    assert float(fetched['rating']) == 4.5

    # Upsert with updated rating
    sample_restaurant['rating'] = 4.8
    updated_id = save_restaurant(sample_restaurant, location_id=loc_id, workspace_id='T_TEST')
    assert updated_id == restaurant_id  # Same row

    fetched = get_restaurant_by_place_id('ChIJtest123')
    assert float(fetched['rating']) == 4.8


def test_vote_toggle(app_context, clean_tables, sample_restaurant, app):
    """INFRA-03: Vote toggle INSERT/DELETE pattern works (D-04)."""
    from lunchbot.client.db_client import save_restaurant, upsert_suggestion, toggle_vote, get_votes

    loc_id = _ensure_workspace_and_location(app)
    restaurant_id = save_restaurant(sample_restaurant, location_id=loc_id, workspace_id='T_TEST')
    today = date.today()
    upsert_suggestion(today, restaurant_id, workspace_id='T_TEST', slack_channel_id='C_TEST')

    votes = get_votes(today)
    assert len(votes) == 1
    poll_option_id = votes[0]['id']

    # Add vote
    result = toggle_vote(poll_option_id, 'U123')
    assert result == 'added'

    votes = get_votes(today)
    assert 'U123' in votes[0]['votes']

    # Remove vote (toggle)
    result = toggle_vote(poll_option_id, 'U123')
    assert result == 'removed'

    votes = get_votes(today)
    assert 'U123' not in votes[0]['votes']


def test_add_emoji(app_context, clean_tables, sample_restaurant, app):
    """INFRA-03: Emoji update works for multiple restaurants."""
    from lunchbot.client.db_client import save_restaurant, add_emoji, get_restaurant_by_place_id

    loc_id = _ensure_workspace_and_location(app)
    save_restaurant(sample_restaurant, location_id=loc_id, workspace_id='T_TEST')
    count = add_emoji(['ChIJtest123'], ':pizza:')
    assert count == 1

    fetched = get_restaurant_by_place_id('ChIJtest123')
    assert fetched['emoji'] == ':pizza:'


def test_unique_vote_constraint(app_context, clean_tables, sample_restaurant, app):
    """D-04: Unique constraint prevents duplicate votes."""
    from lunchbot.client.db_client import save_restaurant, upsert_suggestion, toggle_vote, get_votes
    from psycopg.errors import UniqueViolation

    loc_id = _ensure_workspace_and_location(app)
    restaurant_id = save_restaurant(sample_restaurant, location_id=loc_id, workspace_id='T_TEST')
    today = date.today()
    upsert_suggestion(today, restaurant_id, workspace_id='T_TEST', slack_channel_id='C_TEST')

    votes = get_votes(today)
    poll_option_id = votes[0]['id']

    # Insert vote via toggle
    toggle_vote(poll_option_id, 'U999')

    # Direct INSERT should violate unique constraint
    from lunchbot.db import get_pool
    with pytest.raises(UniqueViolation):
        pool = get_pool()
        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO votes (poll_option_id, user_id) VALUES (%s, %s)",
                (poll_option_id, 'U999')
            )


def test_upsert_suggestion_requires_channel_id():
    """D-11: upsert_suggestion without slack_channel_id arg raises TypeError."""
    from lunchbot.client.db_client import upsert_suggestion
    today = date.today()
    # Calling without the required slack_channel_id positional arg should raise TypeError
    with pytest.raises(TypeError):
        upsert_suggestion(today, 1, 'T1')
