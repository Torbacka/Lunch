"""Unit tests for tenant middleware and signature verification."""
import json
import hmac
import hashlib
import time
import pytest


class TestExtractWorkspaceId:
    """Test extract_workspace_id from various Slack payload formats."""

    def test_slash_command_form_data(self, app):
        """Slash commands send team_id as form data."""
        from lunchbot.middleware.tenant import extract_workspace_id
        with app.test_request_context(
            '/action', method='POST',
            data={'team_id': 'T_ALPHA', 'command': '/lunch'}
        ):
            from flask import request
            assert extract_workspace_id(request) == 'T_ALPHA'

    def test_interactive_payload(self, app):
        """Interactive actions send JSON in form field 'payload'."""
        from lunchbot.middleware.tenant import extract_workspace_id
        payload = json.dumps({'team': {'id': 'T_BRAVO'}, 'type': 'block_actions'})
        with app.test_request_context(
            '/action', method='POST',
            data={'payload': payload}
        ):
            from flask import request
            assert extract_workspace_id(request) == 'T_BRAVO'

    def test_events_api_json_body(self, app):
        """Events API sends team_id in JSON body."""
        from lunchbot.middleware.tenant import extract_workspace_id
        with app.test_request_context(
            '/slack/events', method='POST',
            json={'team_id': 'T_CHARLIE', 'event': {'type': 'app_uninstalled'}}
        ):
            from flask import request
            assert extract_workspace_id(request) == 'T_CHARLIE'

    def test_no_team_id_returns_none(self, app):
        """Empty request returns None."""
        from lunchbot.middleware.tenant import extract_workspace_id
        with app.test_request_context('/health', method='GET'):
            from flask import request
            assert extract_workspace_id(request) is None


class TestVerifySlackSignature:
    """Test Slack signature verification middleware."""

    def test_skips_health_endpoint(self, app):
        """Health endpoint is not verified."""
        with app.test_request_context('/health', method='GET'):
            from lunchbot.middleware.signature import verify_slack_signature
            result = verify_slack_signature()
            assert result is None

    def test_skips_install_endpoint(self, app):
        """OAuth install endpoint is not verified."""
        with app.test_request_context('/slack/install', method='GET'):
            from lunchbot.middleware.signature import verify_slack_signature
            result = verify_slack_signature()
            assert result is None

    def test_skips_oauth_redirect(self, app):
        """OAuth redirect endpoint is not verified."""
        with app.test_request_context('/slack/oauth_redirect', method='GET'):
            from lunchbot.middleware.signature import verify_slack_signature
            result = verify_slack_signature()
            assert result is None

    def test_rejects_invalid_signature(self, app):
        """Invalid signature returns 403."""
        app.config['SLACK_SIGNING_SECRET'] = 'test-signing-secret'
        with app.test_request_context(
            '/action', method='POST',
            data='test=data',
            headers={
                'X-Slack-Request-Timestamp': str(int(time.time())),
                'X-Slack-Signature': 'v0=invalidsignature'
            }
        ):
            from lunchbot.middleware.signature import verify_slack_signature
            with pytest.raises(Exception) as exc_info:
                verify_slack_signature()
            # Flask abort raises a 403 Forbidden
            assert '403' in str(exc_info.value) or exc_info.value.code == 403

    def test_accepts_valid_signature(self, app):
        """Valid HMAC-SHA256 signature passes verification."""
        signing_secret = 'test-signing-secret-for-valid'
        app.config['SLACK_SIGNING_SECRET'] = signing_secret
        timestamp = str(int(time.time()))
        body = b'team_id=T123&command=%2Flunch'
        sig_basestring = f'v0:{timestamp}:{body.decode()}'
        signature = 'v0=' + hmac.new(
            signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
        ).hexdigest()
        with app.test_request_context(
            '/action', method='POST',
            data=body,
            headers={
                'X-Slack-Request-Timestamp': timestamp,
                'X-Slack-Signature': signature
            }
        ):
            from lunchbot.middleware.signature import verify_slack_signature
            result = verify_slack_signature()
            assert result is None  # None means allowed


class TestExecuteWithTenant:
    """Test the tenant-scoped query execution helper."""

    @pytest.mark.db
    def test_sets_tenant_context(self, app, clean_all_tables):
        """execute_with_tenant sets app.current_tenant before query."""
        from lunchbot.db import execute_with_tenant
        with app.test_request_context('/action', method='POST'):
            from flask import g
            g.workspace_id = 'T_TEST'
            # current_setting should return the tenant we set
            result = execute_with_tenant(
                "SELECT current_setting('app.current_tenant', true) AS tenant",
                fetch='one'
            )
            assert result['tenant'] == 'T_TEST'
