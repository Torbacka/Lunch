"""Tests for Alembic migration up/down (INFRA-04)."""
import os
import subprocess
import pytest

pytestmark = pytest.mark.db

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), '..', 'migrations')


def test_upgrade_head():
    """INFRA-04: alembic upgrade head succeeds."""
    result = subprocess.run(
        ['alembic', 'upgrade', 'head'],
        cwd=MIGRATIONS_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"upgrade failed: {result.stderr}"


def test_downgrade_base():
    """INFRA-04: alembic downgrade base succeeds."""
    # First ensure we're at head
    subprocess.run(
        ['alembic', 'upgrade', 'head'],
        cwd=MIGRATIONS_DIR,
        capture_output=True,
    )
    result = subprocess.run(
        ['alembic', 'downgrade', 'base'],
        cwd=MIGRATIONS_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"downgrade failed: {result.stderr}"

    # Restore to head for other tests
    subprocess.run(
        ['alembic', 'upgrade', 'head'],
        cwd=MIGRATIONS_DIR,
        capture_output=True,
    )


def test_migration_current_shows_head():
    """INFRA-04: After upgrade, current revision matches head."""
    subprocess.run(
        ['alembic', 'upgrade', 'head'],
        cwd=MIGRATIONS_DIR,
        capture_output=True,
    )
    result = subprocess.run(
        ['alembic', 'current'],
        cwd=MIGRATIONS_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert '001' in result.stdout, f"Expected revision 001 in: {result.stdout}"
