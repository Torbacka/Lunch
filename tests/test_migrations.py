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


def test_downgrade_base():
    """INFRA-04: alembic downgrade base succeeds."""
    # First ensure we're at head
    subprocess.run(
        ['alembic', 'upgrade', 'head'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        env=ALEMBIC_ENV,
    )
    result = subprocess.run(
        ['alembic', 'downgrade', 'base'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=ALEMBIC_ENV,
    )
    assert result.returncode == 0, f"downgrade failed: {result.stdout}{result.stderr}"

    # Restore to head for other tests
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
    assert '003' in result.stdout, f"Expected revision 003 in: {result.stdout}"
