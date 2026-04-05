"""Tenant context middleware for multi-tenancy.

Extracts workspace_id from Slack payloads and stores in flask.g.
"""
import json
import logging
from flask import g, request

logger = logging.getLogger(__name__)


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
    """Flask before_request hook. Sets g.workspace_id from Slack payload."""
    workspace_id = extract_workspace_id(request)
    if workspace_id:
        g.workspace_id = workspace_id
        logger.debug('Tenant context set: %s', workspace_id)
    else:
        g.workspace_id = None
