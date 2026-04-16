"""Tests for Alembic migration up/down (INFRA-04)."""
import os
import subprocess
import pytest

pytestmark = pytest.mark.db

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
TEST_DB_URL = os.environ.get('TEST_DATABASE_URL', 'postgresql://postgres:dev@localhost:5432/lunchbot_test')
ALEMBIC_ENV = {**os.environ, 'DATABASE_URL': TEST_DB_URL}


def test_upgrade_head():
    """INFRA-04: alembic upgrade head succeeds."""
    result = subprocess.run(
        ['alembic', 'upgrade', 'head'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=ALEMBIC_ENV,
    )
    assert result.returncode == 0, f"upgrade failed: {result.stdout}{result.stderr}"


def test_downgrade_to_008():
    """INFRA-04: alembic downgrade to 008 succeeds (009 is forward-only, downgrade raises)."""
    # First ensure we're at head
    subprocess.run(
        ['alembic', 'upgrade', 'head'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        env=ALEMBIC_ENV,
    )
    # Migration 009 is forward-only (downgrade raises NotImplementedError).
    # Verify that downgrade to 008 correctly fails.
    result = subprocess.run(
        ['alembic', 'downgrade', '008'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=ALEMBIC_ENV,
    )
    assert result.returncode != 0, "009 is forward-only; downgrade should fail"
    assert 'NotImplementedError' in result.stderr or 'forward-only' in result.stderr

    # Ensure we're still at head for other tests
    subprocess.run(
        ['alembic', 'upgrade', 'head'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        env=ALEMBIC_ENV,
    )


def test_migration_current_shows_head():
    """INFRA-04: After upgrade, current revision matches head."""
    subprocess.run(
        ['alembic', 'upgrade', 'head'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        env=ALEMBIC_ENV,
    )
    result = subprocess.run(
        ['alembic', 'current'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=ALEMBIC_ENV,
    )
    assert result.returncode == 0
    assert '009' in result.stdout, f"Expected revision 009 in: {result.stdout}"
