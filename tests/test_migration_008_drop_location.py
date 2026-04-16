"""Tests for migration 008: drop workspaces.location column.

Post-migration-009: downgrade tests that go below 009 are no longer possible
because 009 is a forward-only migration. Only the upgrade-head assertion remains.
"""
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


def test_migration_008_downgrade_blocked_by_009():
    """Migration 009 is forward-only; downgrade to 007 should fail."""
    _alembic('upgrade', 'head')
    down = _alembic('downgrade', '007')
    assert down.returncode != 0, "009 is forward-only; downgrade should fail"
    # Ensure we're still at head
    _alembic('upgrade', 'head')
