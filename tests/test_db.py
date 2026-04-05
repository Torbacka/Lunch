"""Tests for PostgreSQL schema and db_client CRUD operations (INFRA-03)."""
import pytest
from datetime import date


pytestmark = pytest.mark.db


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


def test_restaurant_upsert(app_context, clean_tables, sample_restaurant):
    """INFRA-03: Restaurant upsert creates and updates correctly."""
    from lunchbot.client.db_client import save_restaurant, get_restaurant_by_place_id

    restaurant_id = save_restaurant(sample_restaurant)
    assert restaurant_id is not None
    assert isinstance(restaurant_id, int)

    # Verify retrieval
    fetched = get_restaurant_by_place_id('ChIJtest123')
    assert fetched is not None
    assert fetched['name'] == 'Test Restaurant'
    assert float(fetched['rating']) == 4.5

    # Upsert with updated rating
    sample_restaurant['rating'] = 4.8
    updated_id = save_restaurant(sample_restaurant)
    assert updated_id == restaurant_id  # Same row

    fetched = get_restaurant_by_place_id('ChIJtest123')
    assert float(fetched['rating']) == 4.8


def test_vote_toggle(app_context, clean_tables, sample_restaurant):
    """INFRA-03: Vote toggle INSERT/DELETE pattern works (D-04)."""
    from lunchbot.client.db_client import save_restaurant, upsert_suggestion, toggle_vote, get_votes

    restaurant_id = save_restaurant(sample_restaurant)
    today = date.today()
    upsert_suggestion(today, restaurant_id)

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


def test_add_emoji(app_context, clean_tables, sample_restaurant):
    """INFRA-03: Emoji update works for multiple restaurants."""
    from lunchbot.client.db_client import save_restaurant, add_emoji, get_restaurant_by_place_id

    save_restaurant(sample_restaurant)
    count = add_emoji(['ChIJtest123'], ':pizza:')
    assert count == 1

    fetched = get_restaurant_by_place_id('ChIJtest123')
    assert fetched['emoji'] == ':pizza:'


def test_unique_vote_constraint(app_context, clean_tables, sample_restaurant):
    """D-04: Unique constraint prevents duplicate votes."""
    from lunchbot.client.db_client import save_restaurant, upsert_suggestion, toggle_vote, get_votes
    from psycopg.errors import UniqueViolation

    restaurant_id = save_restaurant(sample_restaurant)
    today = date.today()
    upsert_suggestion(today, restaurant_id)

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
