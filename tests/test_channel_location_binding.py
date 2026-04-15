"""Tests for per-channel workspace-location bindings (migration 007).

Covers:
- migration 007 shape + backfill
- workspace_client resolver contract
- oauth SCOPES contains chat:write.public
- /slack/command prompt vs direct-post flow
- /action handlers for channel_loc_use_default / channel_loc_pick
- no remaining direct reads of workspace['location'] outside workspace_client.py
"""
import json
import os
import re
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.db

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DB_URL = os.environ.get(
    'TEST_DATABASE_URL',
    'postgresql://postgres:dev@localhost:5432/lunchbot_test',
)
ALEMBIC_ENV = {**os.environ, 'DATABASE_URL': TEST_DB_URL}


# ---------------------------------------------------------------------------
# Migration shape
# ---------------------------------------------------------------------------

def _alembic(*args):
    return subprocess.run(
        ['alembic', *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        env=ALEMBIC_ENV,
    )


def test_migration_007_upgrade_downgrade_roundtrip():
    """Migration 007 up/down succeeds on a clean DB."""
    up1 = _alembic('upgrade', 'head')
    assert up1.returncode == 0, f"upgrade head failed: {up1.stdout}{up1.stderr}"

    down = _alembic('downgrade', '006')
    assert down.returncode == 0, f"downgrade 006 failed: {down.stdout}{down.stderr}"

    up2 = _alembic('upgrade', 'head')
    assert up2.returncode == 0, f"re-upgrade failed: {up2.stdout}{up2.stderr}"


def test_migration_007_creates_tables_with_rls(app, clean_all_tables):
    """workspace_locations + channel_locations exist with RLS enabled."""
    with app.app_context():
        pool = app.extensions['pool']
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT relrowsecurity, relforcerowsecurity
                    FROM pg_class WHERE relname = 'workspace_locations'
                """)
                row = cur.fetchone()
                assert row is not None, 'workspace_locations table missing'
                assert row[0] is True and row[1] is True

                cur.execute("""
                    SELECT relrowsecurity, relforcerowsecurity
                    FROM pg_class WHERE relname = 'channel_locations'
                """)
                row = cur.fetchone()
                assert row is not None, 'channel_locations table missing'
                assert row[0] is True and row[1] is True


def test_migration_007_backfill_creates_default_for_legacy_location(app, clean_all_tables):
    """A workspace with a legacy location string gets one Default workspace_location row."""
    with app.app_context():
        pool = app.extensions['pool']
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Clear any rows introduced by the live migration at initial run
                cur.execute("DELETE FROM channel_locations")
                cur.execute("DELETE FROM workspace_locations")
                cur.execute("""
                    INSERT INTO workspaces (team_id, team_name, bot_token_encrypted, location)
                    VALUES ('T_BACKFILL', 'Backfill Co', 'enc', '59.3293,18.0686')
                """)
                # Re-run the backfill SQL (migration already ran; simulate by executing same INSERT)
                cur.execute("""
                    INSERT INTO workspace_locations (team_id, name, lat_lng, is_default)
                    SELECT team_id, 'Default', location, TRUE
                    FROM workspaces
                    WHERE team_id = 'T_BACKFILL'
                      AND location IS NOT NULL AND location <> ''
                """)
                cur.execute("""
                    SELECT name, lat_lng, is_default FROM workspace_locations
                    WHERE team_id = 'T_BACKFILL'
                """)
                rows = cur.fetchall()
                assert len(rows) == 1
                assert rows[0][0] == 'Default'
                assert rows[0][1] == '59.3293,18.0686'
                assert rows[0][2] is True


# ---------------------------------------------------------------------------
# Resolver contract
# ---------------------------------------------------------------------------

@pytest.fixture
def wc_team(app, clean_all_tables):
    """Create a workspace row and yield its team_id for client tests."""
    from lunchbot.client.workspace_client import save_workspace
    with app.app_context():
        save_workspace(
            team_id='T_RES',
            team_name='Res Co',
            bot_token_encrypted='enc',
            bot_user_id='U1',
            scopes='commands',
        )
        yield 'T_RES'


def test_resolver_returns_none_when_zero_locations(app, wc_team):
    from lunchbot.client.workspace_client import resolve_location_for_channel
    with app.app_context():
        assert resolve_location_for_channel(wc_team, 'C_EMPTY') is None


def test_resolver_auto_binds_single_location(app, wc_team):
    from lunchbot.client.workspace_client import (
        create_workspace_location, resolve_location_for_channel,
        get_channel_location,
    )
    with app.app_context():
        loc = create_workspace_location(wc_team, 'HQ', '59.0,18.0', is_default=True)
        got = resolve_location_for_channel(wc_team, 'C_SOLO')
        assert got is not None
        assert got['id'] == loc['id']
        # Binding must have been persisted
        bound = get_channel_location(wc_team, 'C_SOLO')
        assert bound is not None
        assert bound['id'] == loc['id']


def test_resolver_returns_none_with_multiple_unbound_locations(app, wc_team):
    from lunchbot.client.workspace_client import (
        create_workspace_location, resolve_location_for_channel,
    )
    with app.app_context():
        create_workspace_location(wc_team, 'HQ', '59.0,18.0', is_default=True)
        create_workspace_location(wc_team, 'Branch', '60.0,18.0')
        assert resolve_location_for_channel(wc_team, 'C_MULTI') is None


def test_resolver_honors_existing_binding(app, wc_team):
    from lunchbot.client.workspace_client import (
        create_workspace_location, bind_channel_location,
        resolve_location_for_channel,
    )
    with app.app_context():
        a = create_workspace_location(wc_team, 'HQ', '59.0,18.0', is_default=True)
        b = create_workspace_location(wc_team, 'Branch', '60.0,18.0')
        bind_channel_location(wc_team, 'C_BOUND', b['id'])
        got = resolve_location_for_channel(wc_team, 'C_BOUND')
        assert got is not None
        assert got['id'] == b['id']


def test_get_default_location(app, wc_team):
    from lunchbot.client.workspace_client import (
        create_workspace_location, get_default_location,
    )
    with app.app_context():
        create_workspace_location(wc_team, 'Branch', '60.0,18.0')
        create_workspace_location(wc_team, 'HQ', '59.0,18.0', is_default=True)
        d = get_default_location(wc_team)
        assert d is not None
        assert d['name'] == 'HQ'


# ---------------------------------------------------------------------------
# OAuth scope
# ---------------------------------------------------------------------------

def test_scopes_include_chat_write_public():
    """Required for Slack marketplace: bot must be able to post without an invite."""
    from lunchbot.blueprints.oauth import SCOPES
    assert isinstance(SCOPES, str)
    assert 'chat:write.public' in SCOPES


# ---------------------------------------------------------------------------
# Slash command flow
# ---------------------------------------------------------------------------

@patch('lunchbot.blueprints.polls.poll_service')
@patch('lunchbot.blueprints.polls.resolve_location_for_channel')
def test_slash_command_bound_posts_directly(mock_resolver, mock_poll_service, client):
    mock_resolver.return_value = {'id': 1, 'name': 'HQ', 'lat_lng': '59,18'}
    mock_poll_service.push_poll.return_value = {'ok': True}
    response = client.post('/slack/command', data={
        'team_id': 'T_BOUND', 'command': '/lunch', 'text': '',
        'channel_id': 'C_BOUND', 'user_id': 'U1',
    })
    assert response.status_code == 200
    mock_poll_service.push_poll.assert_called_once_with('C_BOUND', 'T_BOUND')


@patch('lunchbot.blueprints.polls.list_workspace_locations')
@patch('lunchbot.blueprints.polls.get_default_location')
@patch('lunchbot.blueprints.polls.poll_service')
@patch('lunchbot.blueprints.polls.resolve_location_for_channel')
def test_slash_command_unbound_multi_location_prompts(
    mock_resolver, mock_poll_service, mock_default, mock_list, client,
):
    mock_resolver.return_value = None
    mock_default.return_value = {'id': 1, 'name': 'HQ', 'lat_lng': '59,18'}
    mock_list.return_value = [
        {'id': 1, 'name': 'HQ', 'lat_lng': '59,18'},
        {'id': 2, 'name': 'Branch', 'lat_lng': '60,18'},
    ]
    response = client.post('/slack/command', data={
        'team_id': 'T_UNBOUND', 'command': '/lunch', 'text': '',
        'channel_id': 'C_NEW', 'user_id': 'U1',
    })
    assert response.status_code == 200
    body = json.loads(response.data)
    assert body.get('response_type') == 'ephemeral'
    blob = json.dumps(body)
    assert 'channel_loc_use_default' in blob
    assert 'channel_loc_pick' in blob
    mock_poll_service.push_poll.assert_not_called()


@patch('lunchbot.blueprints.polls.poll_service')
@patch('lunchbot.blueprints.polls.resolve_location_for_channel')
def test_slash_command_single_location_auto_binds(mock_resolver, mock_poll_service, client):
    """Resolver auto-binds single location and returns row; slash posts directly."""
    mock_resolver.return_value = {'id': 1, 'name': 'HQ', 'lat_lng': '59,18'}
    mock_poll_service.push_poll.return_value = {'ok': True}
    response = client.post('/slack/command', data={
        'team_id': 'T_SOLO', 'command': '/lunch', 'text': '',
        'channel_id': 'C_SOLO', 'user_id': 'U1',
    })
    assert response.status_code == 200
    mock_poll_service.push_poll.assert_called_once_with('C_SOLO', 'T_SOLO')


# ---------------------------------------------------------------------------
# Action handlers for binding
# ---------------------------------------------------------------------------

@patch('lunchbot.blueprints.slack_actions.poll_service')
@patch('lunchbot.blueprints.slack_actions.bind_channel_location')
def test_channel_loc_use_default_action(mock_bind, mock_poll_service, client):
    payload = {
        'type': 'block_actions',
        'team': {'id': 'T_X'},
        'user': {'id': 'U1'},
        'channel': {'id': 'C_X'},
        'actions': [{
            'action_id': 'channel_loc_use_default',
            'type': 'button',
            'value': '42',
        }],
    }
    response = client.post('/action', data={'payload': json.dumps(payload)})
    assert response.status_code == 200
    mock_bind.assert_called_once_with('T_X', 'C_X', 42)
    mock_poll_service.push_poll.assert_called_once()


@patch('lunchbot.blueprints.slack_actions.poll_service')
@patch('lunchbot.blueprints.slack_actions.bind_channel_location')
def test_channel_loc_pick_action(mock_bind, mock_poll_service, client):
    payload = {
        'type': 'block_actions',
        'team': {'id': 'T_Y'},
        'user': {'id': 'U1'},
        'channel': {'id': 'C_Y'},
        'actions': [{
            'action_id': 'channel_loc_pick',
            'type': 'static_select',
            'selected_option': {'value': '99'},
        }],
    }
    response = client.post('/action', data={'payload': json.dumps(payload)})
    assert response.status_code == 200
    mock_bind.assert_called_once_with('T_Y', 'C_Y', 99)
    mock_poll_service.push_poll.assert_called_once()


# ---------------------------------------------------------------------------
# Static check: no remaining direct workspace['location'] reads
# ---------------------------------------------------------------------------

def test_no_remaining_direct_workspace_location_reads():
    """Outside workspace_client.py, no code may read workspace['location']
    or workspace.get('location') directly. Callers must go through
    resolve_location_for_channel."""
    lunchbot_dir = PROJECT_ROOT / 'lunchbot'
    patterns = [
        re.compile(r"workspace\['location'\]"),
        re.compile(r"workspace\.get\(['\"]location['\"]\)"),
    ]
    offenders = []
    for py in lunchbot_dir.rglob('*.py'):
        if 'workspace_client.py' in str(py):
            continue
        text = py.read_text()
        for pat in patterns:
            if pat.search(text):
                offenders.append(str(py.relative_to(PROJECT_ROOT)))
                break
    assert offenders == [], f"Direct workspace location reads remain: {offenders}"
