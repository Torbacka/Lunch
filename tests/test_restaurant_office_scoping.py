"""Database integration tests for office-owned restaurant suggestions."""
from datetime import date

import pytest
from flask import g


pytestmark = pytest.mark.db


def _seed_workspace_and_offices(conn):
    conn.execute("""
        INSERT INTO workspaces (team_id, team_name, bot_token_encrypted)
        VALUES ('T_OFFICE', 'Office Test', 'token')
    """)
    office_a = conn.execute("""
        INSERT INTO workspace_locations (team_id, name, lat_lng, is_default)
        VALUES ('T_OFFICE', 'Office A', '59.3,18.0', TRUE) RETURNING id
    """).fetchone()[0]
    office_b = conn.execute("""
        INSERT INTO workspace_locations (team_id, name, lat_lng, is_default)
        VALUES ('T_OFFICE', 'Office B', '59.4,18.1', FALSE) RETURNING id
    """).fetchone()[0]
    conn.execute("""
        INSERT INTO channel_locations (team_id, channel_id, location_id)
        VALUES ('T_OFFICE', 'C_A', %s), ('T_OFFICE', 'C_B', %s)
    """, (office_a, office_b))
    return office_a, office_b


def test_same_google_place_can_belong_to_two_offices(
    app, app_context, clean_all_tables_with_stats, sample_restaurant,
):
    from lunchbot.client import db_client

    with app.extensions['pool'].connection() as conn:
        office_a, office_b = _seed_workspace_and_offices(conn)

    g.workspace_id = 'T_OFFICE'
    first = db_client.save_restaurant(sample_restaurant, office_a, 'T_OFFICE')
    second = db_client.save_restaurant(sample_restaurant, office_b, 'T_OFFICE')

    assert first != second
    assert db_client.get_restaurant_by_place_id(
        sample_restaurant['place_id'], office_a,
    )['id'] == first
    assert db_client.get_restaurant_by_place_id(
        sample_restaurant['place_id'], office_b,
    )['id'] == second


def test_cross_office_poll_insert_is_rejected(
    app, app_context, clean_all_tables_with_stats, sample_restaurant,
):
    from lunchbot.client import db_client

    with app.extensions['pool'].connection() as conn:
        office_a, _ = _seed_workspace_and_offices(conn)

    g.workspace_id = 'T_OFFICE'
    restaurant_id = db_client.save_restaurant(sample_restaurant, office_a, 'T_OFFICE')

    assert db_client.upsert_suggestion(
        date.today(), restaurant_id, 'T_OFFICE', 'C_B',
    ) is None
    assert db_client.upsert_suggestion(
        date.today(), restaurant_id, 'T_OFFICE', 'C_A',
    ) is not None


def test_custom_restaurants_dedupe_within_office_only(
    app, app_context, clean_all_tables_with_stats,
):
    from lunchbot.client import db_client

    with app.extensions['pool'].connection() as conn:
        office_a, office_b = _seed_workspace_and_offices(conn)

    g.workspace_id = 'T_OFFICE'
    first = db_client.save_custom_restaurant('Cafe  Test', office_a, 'T_OFFICE')
    duplicate = db_client.save_custom_restaurant(' cafe test ', office_a, 'T_OFFICE')
    other_office = db_client.save_custom_restaurant('Cafe Test', office_b, 'T_OFFICE')

    assert first['id'] == duplicate['id']
    assert first['id'] != other_office['id']


def test_custom_restaurant_is_candidate_for_its_office_only(
    app, app_context, clean_all_tables_with_stats,
):
    from lunchbot.client import db_client

    with app.extensions['pool'].connection() as conn:
        office_a, _ = _seed_workspace_and_offices(conn)

    g.workspace_id = 'T_OFFICE'
    custom = db_client.save_custom_restaurant(
        'Unlisted Cafe', office_a, 'T_OFFICE',
    )

    office_a_pool = db_client.get_candidate_pool(date.today(), 'C_A')
    office_b_pool = db_client.get_candidate_pool(date.today(), 'C_B')

    assert [candidate['restaurant_id'] for candidate in office_a_pool] == [
        custom['id'],
    ]
    assert office_b_pool == []
