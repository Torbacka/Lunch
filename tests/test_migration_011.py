"""Schema invariants for office-scoped and custom restaurant identity."""
import pytest


pytestmark = pytest.mark.db


def test_restaurant_source_columns_and_office_unique_key(app_context, app):
    pool = app.extensions['pool']
    with pool.connection() as conn:
        columns = conn.execute("""
            SELECT column_name, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'restaurants'
              AND column_name IN ('source', 'normalized_name')
        """).fetchall()
        definition = conn.execute("""
            SELECT pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conname = 'restaurants_workspace_location_place_key'
        """).fetchone()

    assert dict(columns) == {'source': 'NO', 'normalized_name': 'YES'}
    assert definition is not None
    assert 'workspace_id, location_id, place_id' in definition[0]
