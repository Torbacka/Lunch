"""Unit tests for smart recommendation config and algorithm.

Tests for BOT-07 (admin config), BOT-05 (Thompson sampling), BOT-06 (random fill).
"""
import os
import pytest


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


# --- Algorithm stub tests (BOT-05, BOT-06, BOT-11) — implemented in Plan 02 ---

@pytest.mark.skip(reason="Plan 02")
def test_thompson_sampling_selects_top_n():
    """Thompson sampling selects top N candidates by sampled Beta score."""
    pass


@pytest.mark.skip(reason="Plan 02")
def test_random_fill_excludes_today():
    """Random fill excludes restaurants already in today's poll."""
    pass


@pytest.mark.skip(reason="Plan 02")
def test_ensure_poll_options_preserves_manual():
    """ensure_poll_options preserves manually-added poll options."""
    pass
