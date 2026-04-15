"""Slack request signature verification middleware."""
import logging
from flask import request, abort, current_app
from slack_sdk.signature import SignatureVerifier

logger = logging.getLogger(__name__)

# Paths that skip signature verification
SKIP_PATHS = frozenset(['/health', '/metrics', '/slack/install', '/slack/oauth_redirect', '/slack/setup', '/seed', '/lunch_message', '/', '/privacy', '/support', '/places/autocomplete', '/places/details'])


def verify_slack_signature():
    """Flask before_request hook. Verifies Slack signing secret on incoming requests.
    Skips /health, /slack/install, /slack/oauth_redirect.
    Returns None to allow request, or aborts 403.
    """
    if request.path in SKIP_PATHS:
        return None

    signing_secret = current_app.config.get('SLACK_SIGNING_SECRET')
    if not signing_secret:
        logger.warning('SLACK_SIGNING_SECRET not configured, skipping verification')
        return None

    verifier = SignatureVerifier(signing_secret)
    if not verifier.is_valid_request(request.get_data(), request.headers):
        logger.warning('Invalid Slack signature for %s', request.path)
        abort(403, 'Invalid Slack signature')

    return None
