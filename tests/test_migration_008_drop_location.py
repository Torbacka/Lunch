"""Tests for migration 008: drop workspaces.location column."""
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.db

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DB_URL = os.environ.get(
    'TEST_DATABASE_URL',
    'postgresql://postgres:dev@localhost:5432/lunchbot_test',
)
ALEMBIC_ENV = {**os.environ, 'DATABASE_URL': TEST_DB_URL}


def _alembic(*args):
    return subprocess.run(
        ['alembic', *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        env=ALEMBIC_ENV,
    )


def test_migration_008_drops_location_column(app, clean_all_tables):
    up = _alembic('upgrade', 'head')
    assert up.returncode == 0, f"upgrade head failed: {up.stdout}{up.stderr}"
    with app.app_context():
        from lunchbot.db import get_pool
        with get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'workspaces' AND column_name = 'location'
                """)
                assert cur.fetchone() is None, 'workspaces.location column should be dropped'


def test_migration_008_downgrade_readds_column(app, clean_all_tables):
    # Ensure we are at head first
    _alembic('upgrade', 'head')
    down = _alembic('downgrade', '007')
    assert down.returncode == 0, f"downgrade 007 failed: {down.stdout}{down.stderr}"
    with app.app_context():
        from lunchbot.db import get_pool
        with get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'workspaces' AND column_name = 'location'
                """)
                assert cur.fetchone() is not None
    # Re-upgrade to leave the DB in the head state for other tests
    up = _alembic('upgrade', 'head')
    assert up.returncode == 0


def test_migration_008_backfills_legacy_location(app, clean_all_tables):
    """A workspace with a legacy location and no workspace_locations row
    must get a Main Office created during upgrade."""
    # Downgrade to before 008 so we can insert a legacy-state workspace
    _alembic('downgrade', '007')
    with app.app_context():
        from lunchbot.db import get_pool
        with get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM channel_locations")
                cur.execute("DELETE FROM workspace_locations")
                cur.execute("""
                    INSERT INTO workspaces (team_id, team_name, bot_token_encrypted, location)
                    VALUES ('T_LEGACY', 'Legacy Co', 'enc', '59.3293,18.0686')
                """)

    up = _alembic('upgrade', 'head')
    assert up.returncode == 0, f"re-upgrade failed: {up.stdout}{up.stderr}"

    with app.app_context():
        from lunchbot.db import get_pool
        with get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SET app.current_tenant = 'T_LEGACY'")
                cur.execute("""
                    SELECT name, lat_lng, is_default FROM workspace_locations
                    WHERE team_id = 'T_LEGACY'
                """)
                rows = cur.fetchall()
                assert len(rows) == 1
                assert rows[0][0] == 'Main Office'
                assert rows[0][1] == '59.3293,18.0686'
                assert rows[0][2] is True
