"""Integration tests for restaurant_stats DB operations.

Tests for BOT-11 (reputation tracking, stats CRUD, candidate pool).
All tests require running PostgreSQL with migration 003 applied.
"""
import pytest


# --- Integration stub tests (BOT-11) — implemented in Plan 02 ---

@pytest.mark.skip(reason="Plan 02")
def test_get_or_create_stats_creates_default():
    """get_or_create_stats creates a row with alpha=1.0, beta=1.0, times_shown=0."""
    pass


@pytest.mark.skip(reason="Plan 02")
def test_get_or_create_stats_returns_existing():
    """get_or_create_stats returns the existing row without modifying it."""
    pass


@pytest.mark.skip(reason="Plan 02")
def test_get_candidate_pool_excludes_today():
    """get_candidate_pool excludes restaurants already in today's poll."""
    pass


@pytest.mark.skip(reason="Plan 02")
def test_update_stats_from_poll_increments_alpha_beta():
    """update_restaurant_stats correctly increments alpha and beta from vote data."""
    pass


@pytest.mark.skip(reason="Plan 02")
def test_update_stats_idempotent():
    """Calling update_restaurant_stats multiple times is tracked by times_shown."""
    pass
