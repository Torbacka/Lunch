"""Tests for office mutation helpers added in Phase 07.1."""
import pytest

pytestmark = pytest.mark.db


@pytest.fixture
def wc_team(app, clean_all_tables):
    from lunchbot.client.workspace_client import save_workspace
    with app.app_context():
        save_workspace(
            team_id='T_OFF',
            team_name='Office Co',
            bot_token_encrypted='enc',
            bot_user_id='U1',
            scopes='commands',
        )
        yield 'T_OFF'


def test_rename_updates_name(app, wc_team):
    from lunchbot.client.workspace_client import (
        create_workspace_location, rename_workspace_location, list_workspace_locations,
    )
    with app.app_context():
        loc = create_workspace_location(wc_team, 'HQ', '59,18', is_default=True)
        updated = rename_workspace_location(wc_team, loc['id'], 'Spotify HQ', 'U1')
        assert updated is not None and updated['name'] == 'Spotify HQ'
        rows = list_workspace_locations(wc_team)
        assert rows[0]['name'] == 'Spotify HQ'


def test_rename_missing_returns_none(app, wc_team):
    from lunchbot.client.workspace_client import rename_workspace_location
    with app.app_context():
        assert rename_workspace_location(wc_team, 99999, 'X', 'U1') is None


def test_rename_blank_name_returns_none(app, wc_team):
    from lunchbot.client.workspace_client import (
        create_workspace_location, rename_workspace_location,
    )
    with app.app_context():
        loc = create_workspace_location(wc_team, 'HQ', '59,18')
        assert rename_workspace_location(wc_team, loc['id'], '   ', 'U1') is None


def test_set_default_clears_previous(app, wc_team):
    from lunchbot.client.workspace_client import (
        create_workspace_location, set_default_workspace_location, list_workspace_locations,
    )
    with app.app_context():
        a = create_workspace_location(wc_team, 'HQ', '59,18', is_default=True)
        b = create_workspace_location(wc_team, 'Branch', '60,18')
        set_default_workspace_location(wc_team, b['id'], 'U1')
        rows = {r['name']: r['is_default'] for r in list_workspace_locations(wc_team)}
        assert rows['HQ'] is False
        assert rows['Branch'] is True


def test_set_default_missing_returns_none(app, wc_team):
    from lunchbot.client.workspace_client import (
        create_workspace_location, set_default_workspace_location,
        list_workspace_locations,
    )
    with app.app_context():
        hq = create_workspace_location(wc_team, 'HQ', '59,18', is_default=True)
        assert set_default_workspace_location(wc_team, 99999, 'U1') is None
        # D-17: the previous default must still be marked default after a failed call.
        rows = {r['id']: r['is_default'] for r in list_workspace_locations(wc_team)}
        assert rows[hq['id']] is True


def test_delete_cascades_channel_bindings(app, wc_team):
    from lunchbot.client.workspace_client import (
        create_workspace_location, bind_channel_location, get_channel_location,
        delete_workspace_location,
    )
    with app.app_context():
        loc = create_workspace_location(wc_team, 'HQ', '59,18', is_default=True)
        bind_channel_location(wc_team, 'C_A', loc['id'])
        bind_channel_location(wc_team, 'C_B', loc['id'])
        assert get_channel_location(wc_team, 'C_A') is not None
        assert delete_workspace_location(wc_team, loc['id'], 'U1') is True
        assert get_channel_location(wc_team, 'C_A') is None
        assert get_channel_location(wc_team, 'C_B') is None


def test_delete_missing_returns_false(app, wc_team):
    from lunchbot.client.workspace_client import delete_workspace_location
    with app.app_context():
        assert delete_workspace_location(wc_team, 99999, 'U1') is False
