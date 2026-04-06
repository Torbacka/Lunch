"""Tenant context middleware for multi-tenancy.

Extracts workspace_id from Slack payloads and stores in flask.g.
Binds request_id (UUID) and workspace_id to structlog context vars for
all log calls within the request (OBS-01, OBS-02).
"""
import json
import uuid

import structlog
from flask import g, request
from structlog.contextvars import bind_contextvars, clear_contextvars

logger = structlog.get_logger(__name__)


def extract_workspace_id(req):
    """Extract team_id from various Slack payload formats.

    - Slash commands: form data with 'team_id' key
    - Interactive actions: JSON in form field 'payload', team_id at payload.team.id
    - Events API: JSON body with 'team_id' key
    Returns team_id string or None.
    """
    # Slash commands: form data with team_id
    if req.form.get('team_id'):
        return req.form['team_id']

    # Interactive actions: JSON payload in form field
    payload_str = req.form.get('payload')
    if payload_str:
        try:
            payload = json.loads(payload_str)
            team = payload.get('team', {})
            return team.get('id') if isinstance(team, dict) else team
        except (json.JSONDecodeError, AttributeError):
            return None

    # Events API: JSON body with team_id
    data = req.get_json(silent=True)
    if data:
        return data.get('team_id')

    return None


def set_tenant_context():
    """Flask before_request hook. Sets g.workspace_id and binds structlog context."""
    # Clear previous request's context vars to prevent leakage
    clear_contextvars()

    # Generate unique request ID for tracing (OBS-02)
    request_id = str(uuid.uuid4())
    g.request_id = request_id

    workspace_id = extract_workspace_id(request)
    if workspace_id:
        g.workspace_id = workspace_id
    else:
        g.workspace_id = None

    # Bind context vars so ALL structlog calls in this request include these fields
    bind_contextvars(
        request_id=request_id,
        workspace_id=workspace_id or 'none',
    )
    logger.debug('tenant_context_set', workspace_id=workspace_id)
