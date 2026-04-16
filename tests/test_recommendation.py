"""Unit tests for smart recommendation config and algorithm.

Tests for BOT-07 (admin config), BOT-05 (Thompson sampling), BOT-06 (random fill).
"""
import os
import pytest
import numpy as np


# --- Config tests (BOT-07) ---

def test_config_poll_size_default(app):
    """Config.POLL_SIZE defaults to 4."""
    assert app.config['POLL_SIZE'] == 4


def test_config_smart_picks_default(app):
    """Config.SMART_PICKS defaults to 2."""
    assert app.config['SMART_PICKS'] == 2


def test_config_poll_size_env_override(monkeypatch):
    """POLL_SIZE env var override is applied at class definition time."""
    monkeypatch.setenv('POLL_SIZE', '6')
    monkeypatch.setenv('SMART_PICKS', '2')
    import importlib
    import lunchbot.config as cfg_module
    importlib.reload(cfg_module)
    assert cfg_module.Config.POLL_SIZE == 6
    # Restore by reloading without env override
    monkeypatch.delenv('POLL_SIZE', raising=False)
    monkeypatch.delenv('SMART_PICKS', raising=False)
    importlib.reload(cfg_module)


def test_config_smart_picks_env_override(monkeypatch):
    """SMART_PICKS env var override is applied at class definition time."""
    monkeypatch.setenv('POLL_SIZE', '5')
    monkeypatch.setenv('SMART_PICKS', '3')
    import importlib
    import lunchbot.config as cfg_module
    importlib.reload(cfg_module)
    assert cfg_module.Config.SMART_PICKS == 3
    monkeypatch.delenv('POLL_SIZE', raising=False)
    monkeypatch.delenv('SMART_PICKS', raising=False)
    importlib.reload(cfg_module)


def test_config_poll_size_clamped_to_minimum(monkeypatch):
    """Non-positive POLL_SIZE is clamped to minimum 1."""
    monkeypatch.setenv('POLL_SIZE', '0')
    import importlib
    import lunchbot.config as cfg_module
    importlib.reload(cfg_module)
    assert cfg_module.Config.POLL_SIZE >= 1
    monkeypatch.delenv('POLL_SIZE', raising=False)
    importlib.reload(cfg_module)


def test_config_smart_picks_clamped_to_poll_size(monkeypatch):
    """SMART_PICKS is clamped to POLL_SIZE when it exceeds it."""
    monkeypatch.setenv('POLL_SIZE', '3')
    monkeypatch.setenv('SMART_PICKS', '10')
    import importlib
    import lunchbot.config as cfg_module
    importlib.reload(cfg_module)
    assert cfg_module.Config.SMART_PICKS <= cfg_module.Config.POLL_SIZE
    assert cfg_module.Config.SMART_PICKS == 3
    monkeypatch.delenv('POLL_SIZE', raising=False)
    monkeypatch.delenv('SMART_PICKS', raising=False)
    importlib.reload(cfg_module)


# --- Algorithm tests (BOT-05, BOT-06) ---

def test_thompson_sampling_selects_top_n():
    """BOT-05: Thompson sampling picks restaurants with highest sampled scores."""
    from lunchbot.services.recommendation_service import thompson_sample
    candidates = [
        {'restaurant_id': 1, 'alpha': 10.0, 'beta': 1.0},  # strong winner
        {'restaurant_id': 2, 'alpha': 1.0, 'beta': 10.0},  # weak
        {'restaurant_id': 3, 'alpha': 5.0, 'beta': 2.0},   # decent
    ]
    rng = np.random.default_rng(42)
    picks = thompson_sample(candidates, n_picks=2, rng=rng)
    assert len(picks) == 2
    # With seed 42 and these alpha/beta, restaurant 1 should be picked
    picked_ids = [p['restaurant_id'] for p in picks]
    assert 1 in picked_ids  # strong winner always in top 2


def test_thompson_sampling_empty_candidates():
    """Thompson sampling with empty candidates returns empty list."""
    from lunchbot.services.recommendation_service import thompson_sample
    assert thompson_sample([], n_picks=2) == []


def test_thompson_sampling_fewer_candidates_than_picks():
    """Thompson sampling with fewer candidates than n_picks returns all candidates."""
    from lunchbot.services.recommendation_service import thompson_sample
    candidates = [{'restaurant_id': 1, 'alpha': 1.0, 'beta': 1.0}]
    picks = thompson_sample(candidates, n_picks=5)
    assert len(picks) == 1


def test_thompson_sampling_returns_exact_n():
    """Thompson sampling returns exactly n_picks when pool is large enough."""
    from lunchbot.services.recommendation_service import thompson_sample
    candidates = [
        {'restaurant_id': i, 'alpha': 1.0, 'beta': 1.0} for i in range(10)
    ]
    picks = thompson_sample(candidates, n_picks=3, rng=np.random.default_rng(0))
    assert len(picks) == 3


def test_random_fill_excludes_ids():
    """BOT-06: Random fill excludes restaurants already in poll."""
    from lunchbot.services.recommendation_service import select_random_fill
    pool = [
        {'restaurant_id': 1, 'name': 'A'},
        {'restaurant_id': 2, 'name': 'B'},
        {'restaurant_id': 3, 'name': 'C'},
    ]
    rng = np.random.default_rng(42)
    fills = select_random_fill(pool, n_fill=2, exclude_ids={1}, rng=rng)
    assert len(fills) == 2
    fill_ids = [f['restaurant_id'] for f in fills]
    assert 1 not in fill_ids


def test_random_fill_empty_pool():
    """Random fill with empty pool returns empty list."""
    from lunchbot.services.recommendation_service import select_random_fill
    assert select_random_fill([], n_fill=3) == []


def test_random_fill_returns_up_to_n():
    """Random fill returns at most n_fill candidates."""
    from lunchbot.services.recommendation_service import select_random_fill
    pool = [
        {'restaurant_id': 1, 'name': 'A'},
        {'restaurant_id': 2, 'name': 'B'},
    ]
    rng = np.random.default_rng(0)
    fills = select_random_fill(pool, n_fill=5, rng=rng)
    # Only 2 in pool, so at most 2
    assert len(fills) <= 2


def test_random_fill_all_excluded():
    """Random fill with all candidates excluded returns empty list."""
    from lunchbot.services.recommendation_service import select_random_fill
    pool = [{'restaurant_id': 1, 'name': 'A'}]
    fills = select_random_fill(pool, n_fill=1, exclude_ids={1})
    assert fills == []


# --- Integration test for push_poll calling ensure_poll_options ---

def test_ensure_poll_options_called_from_push_poll(app_context, monkeypatch):
    """D-04: push_poll triggers ensure_poll_options inline."""
    from unittest.mock import patch
    from lunchbot.services import poll_service

    calls = []
    def mock_ensure(poll_date=None, workspace_id=None, channel_id=None):
        calls.append({'poll_date': poll_date, 'workspace_id': workspace_id, 'channel_id': channel_id})
        return 0

    with patch('lunchbot.services.poll_service.ensure_poll_options', mock_ensure):
        with patch.object(poll_service.slack_client, 'post_message', return_value={'ok': True}):
            with patch.object(poll_service.db_client, 'get_votes', return_value=[]):
                from datetime import date
                poll_service.push_poll('#lunch', 'T_TEST')

    assert len(calls) == 1
    from datetime import date
    assert calls[0]['poll_date'] == date.today()
    assert calls[0]['workspace_id'] == 'T_TEST'
    assert calls[0]['channel_id'] == '#lunch'
