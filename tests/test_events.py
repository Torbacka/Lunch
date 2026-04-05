"""Tests for Slack Events API endpoint.

Handles url_verification, app_uninstalled, tokens_revoked.
TestConfig has SLACK_SIGNING_SECRET=None so signature middleware auto-skips.
"""
import json
import pytest


# ---------------------------------------------------------------------------
# Test: URL verification challenge
# ---------------------------------------------------------------------------

def test_url_verification_challenge(client):
    """POST /slack/events with url_verification type returns challenge."""
    payload = {'type': 'url_verification', 'challenge': 'abc123'}
    response = client.post(
        '/slack/events',
        data=json.dumps(payload),
        content_type='application/json',
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data == {'challenge': 'abc123'}


# ---------------------------------------------------------------------------
# Test: app_uninstalled soft-deletes workspace (DB)
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_app_uninstalled_deactivates_workspace(client, app, clean_all_tables):
    """app_uninstalled event soft-deletes workspace (is_active=False, uninstalled_at set)."""
    with app.app_context():
        from lunchbot.client.workspace_client import save_workspace
        save_workspace('T_UNINSTALL', 'Uninstall Team', 'encrypted-token', 'U_BOT', 'commands')

    payload = {
        'team_id': 'T_UNINSTALL',
        'event': {'type': 'app_uninstalled'},
    }
    response = client.post(
        '/slack/events',
        data=json.dumps(payload),
        content_type='application/json',
    )
    assert response.status_code == 200

    with app.app_context():
        from lunchbot.client.workspace_client import get_workspace
        ws = get_workspace('T_UNINSTALL')

    assert ws is not None
    assert ws['is_active'] is False
    assert ws['uninstalled_at'] is not None


# ---------------------------------------------------------------------------
# Test: tokens_revoked soft-deletes workspace (DB)
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_tokens_revoked_deactivates_workspace(client, app, clean_all_tables):
    """tokens_revoked event soft-deletes workspace (is_active=False, uninstalled_at set)."""
    with app.app_context():
        from lunchbot.client.workspace_client import save_workspace
        save_workspace('T_REVOKE', 'Revoke Team', 'encrypted-token', 'U_BOT', 'commands')

    payload = {
        'team_id': 'T_REVOKE',
        'event': {'type': 'tokens_revoked'},
    }
    response = client.post(
        '/slack/events',
        data=json.dumps(payload),
        content_type='application/json',
    )
    assert response.status_code == 200

    with app.app_context():
        from lunchbot.client.workspace_client import get_workspace
        ws = get_workspace('T_REVOKE')

    assert ws is not None
    assert ws['is_active'] is False
    assert ws['uninstalled_at'] is not None


# ---------------------------------------------------------------------------
# Test: app_uninstalled is idempotent (DB)
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_app_uninstalled_idempotent(client, app, clean_all_tables):
    """Sending app_uninstalled twice does not error and workspace stays is_active=False."""
    with app.app_context():
        from lunchbot.client.workspace_client import save_workspace
        save_workspace('T_IDEMP', 'Idemp Team', 'encrypted-token', 'U_BOT', 'commands')

    payload = {
        'team_id': 'T_IDEMP',
        'event': {'type': 'app_uninstalled'},
    }

    # First uninstall
    response1 = client.post(
        '/slack/events',
        data=json.dumps(payload),
        content_type='application/json',
    )
    assert response1.status_code == 200

    # Second uninstall (idempotent)
    response2 = client.post(
        '/slack/events',
        data=json.dumps(payload),
        content_type='application/json',
    )
    assert response2.status_code == 200

    with app.app_context():
        from lunchbot.client.workspace_client import get_workspace
        ws = get_workspace('T_IDEMP')

    assert ws['is_active'] is False


# ---------------------------------------------------------------------------
# Test: unknown event type returns 200
# ---------------------------------------------------------------------------

def test_unknown_event_returns_200(client):
    """Unknown event type is ignored and returns 200."""
    payload = {
        'team_id': 'T_UNKNOWN',
        'event': {'type': 'member_joined_channel'},
    }
    response = client.post(
        '/slack/events',
        data=json.dumps(payload),
        content_type='application/json',
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Test: missing team_id returns 200
# ---------------------------------------------------------------------------

def test_missing_team_id_returns_200(client):
    """app_uninstalled without team_id logs warning but does not crash (returns 200)."""
    payload = {'event': {'type': 'app_uninstalled'}}
    response = client.post(
        '/slack/events',
        data=json.dumps(payload),
        content_type='application/json',
    )
    assert response.status_code == 200
