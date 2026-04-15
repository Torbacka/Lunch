"""Tests for workspace settings CRUD and migration 005."""
import importlib
import pytest
from unittest.mock import patch


class TestMigration005:
    """Verify migration 005 adds expected columns."""

    def test_migration_005_has_correct_revision(self):
        mod = importlib.import_module('migrations.versions.005_workspace_settings')
        assert mod.revision == '005'
        assert mod.down_revision == '004'

    def test_migration_005_adds_poll_schedule_time(self):
        mod = importlib.import_module('migrations.versions.005_workspace_settings')
        import inspect
        source = inspect.getsource(mod.upgrade)
        assert 'poll_schedule_time' in source
        assert 'TIME' in source

    def test_migration_005_adds_poll_schedule_timezone(self):
        mod = importlib.import_module('migrations.versions.005_workspace_settings')
        import inspect
        source = inspect.getsource(mod.upgrade)
        assert 'poll_schedule_timezone' in source

    def test_migration_005_adds_poll_schedule_weekdays(self):
        mod = importlib.import_module('migrations.versions.005_workspace_settings')
        import inspect
        source = inspect.getsource(mod.upgrade)
        assert 'poll_schedule_weekdays' in source
        assert 'TEXT[]' in source

    def test_migration_005_adds_poll_size(self):
        mod = importlib.import_module('migrations.versions.005_workspace_settings')
        import inspect
        source = inspect.getsource(mod.upgrade)
        assert 'poll_size' in source
        assert 'INTEGER' in source

    def test_migration_005_adds_smart_picks(self):
        mod = importlib.import_module('migrations.versions.005_workspace_settings')
        import inspect
        source = inspect.getsource(mod.upgrade)
        assert 'smart_picks' in source


class TestGetWorkspaceSettings:
    """Tests for get_workspace_settings()."""

    def test_returns_settings_dict_for_existing_workspace(self, app, clean_all_tables):
        with app.app_context():
            from lunchbot.client.workspace_client import save_workspace, get_workspace_settings
            save_workspace('T_SETTINGS', 'Settings Team', 'enc_token', 'U_BOT', 'chat:write')
            result = get_workspace_settings('T_SETTINGS')
            assert result is not None
            assert result['team_id'] == 'T_SETTINGS'
            assert 'poll_channel' in result
            assert 'poll_schedule_time' in result
            assert 'poll_schedule_timezone' in result
            assert 'poll_schedule_weekdays' in result
            assert 'poll_size' in result
            assert 'smart_picks' in result
            # Phase 07.1 plan 03 (migration 008) drops workspaces.location; the
            # get_workspace_settings payload no longer exposes the column.
            assert 'location' not in result

    def test_returns_none_for_missing_workspace(self, app, clean_all_tables):
        with app.app_context():
            from lunchbot.client.workspace_client import get_workspace_settings
            result = get_workspace_settings('T_NONEXISTENT')
            assert result is None

    def test_returns_none_values_for_unconfigured_columns(self, app, clean_all_tables):
        with app.app_context():
            from lunchbot.client.workspace_client import save_workspace, get_workspace_settings
            save_workspace('T_FRESH', 'Fresh Team', 'enc_token', 'U_BOT', 'chat:write')
            result = get_workspace_settings('T_FRESH')
            assert result['poll_schedule_time'] is None
            assert result['poll_schedule_timezone'] is None
            assert result['poll_schedule_weekdays'] is None
            assert result['poll_size'] is None
            assert result['smart_picks'] is None

    def test_returns_none_for_inactive_workspace(self, app, clean_all_tables):
        with app.app_context():
            from lunchbot.client.workspace_client import save_workspace, deactivate_workspace, get_workspace_settings
            save_workspace('T_INACTIVE', 'Inactive Team', 'enc_token', 'U_BOT', 'chat:write')
            deactivate_workspace('T_INACTIVE')
            result = get_workspace_settings('T_INACTIVE')
            assert result is None


class TestUpdateWorkspaceSettings:
    """Tests for update_workspace_settings()."""

    def test_updates_only_provided_columns(self, app, clean_all_tables):
        with app.app_context():
            from lunchbot.client.workspace_client import save_workspace, get_workspace_settings, update_workspace_settings
            save_workspace('T_UPD', 'Update Team', 'enc_token', 'U_BOT', 'chat:write')
            update_workspace_settings('T_UPD', poll_size=6, smart_picks=3)
            result = get_workspace_settings('T_UPD')
            assert result['poll_size'] == 6
            assert result['smart_picks'] == 3
            # Other fields should remain None
            assert result['poll_schedule_time'] is None

    def test_clears_schedule_when_set_to_none(self, app, clean_all_tables):
        with app.app_context():
            from lunchbot.client.workspace_client import save_workspace, get_workspace_settings, update_workspace_settings
            from datetime import time
            save_workspace('T_CLR', 'Clear Team', 'enc_token', 'U_BOT', 'chat:write')
            update_workspace_settings('T_CLR', poll_schedule_time=time(11, 30), poll_schedule_timezone='Europe/Stockholm')
            result = get_workspace_settings('T_CLR')
            assert result['poll_schedule_time'] is not None
            # Now clear it
            update_workspace_settings('T_CLR', poll_schedule_time=None)
            result = get_workspace_settings('T_CLR')
            assert result['poll_schedule_time'] is None
            # Timezone should still be set since we only cleared time
            assert result['poll_schedule_timezone'] == 'Europe/Stockholm'

    def test_rejects_disallowed_columns(self, app, clean_all_tables):
        """Columns not in ALLOWED set should be silently ignored (security: T-05-01)."""
        with app.app_context():
            from lunchbot.client.workspace_client import save_workspace, update_workspace_settings, get_workspace
            save_workspace('T_SEC', 'Security Team', 'enc_token', 'U_BOT', 'chat:write')
            # Try to update a non-allowed column; should be no-op
            update_workspace_settings('T_SEC', bot_token_encrypted='HACKED')
            ws = get_workspace('T_SEC')
            assert ws['bot_token_encrypted'] == 'enc_token'

    def test_noop_when_no_valid_kwargs(self, app, clean_all_tables):
        """Calling with only invalid keys should be a safe no-op."""
        with app.app_context():
            from lunchbot.client.workspace_client import save_workspace, update_workspace_settings
            save_workspace('T_NOOP', 'Noop Team', 'enc_token', 'U_BOT', 'chat:write')
            # Should not raise
            update_workspace_settings('T_NOOP', invalid_col='value')
