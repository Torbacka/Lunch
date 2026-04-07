"""Public web pages for LunchBot.

Endpoints:
  GET /         -- Landing page with "Add to Slack" button
  GET /privacy  -- Privacy policy
  GET /support  -- Support contact page
"""
from flask import Blueprint

bp = Blueprint('web', __name__)


def _nav_html():
    """Shared navigation bar HTML."""
    return """<nav style="border-bottom: 1px solid #D1D5DB; padding: 16px 0;">
<div style="max-width: 720px; margin: 0 auto; padding: 0 16px; display: flex; justify-content: space-between; align-items: center;">
  <a href="/" style="font-size: 16px; font-weight: 600; color: #111827; text-decoration: none;">LunchBot</a>
  <div>
    <a href="/privacy" style="font-size: 14px; font-weight: 400; color: #4A154B; text-decoration: none; margin-left: 24px;">Privacy</a>
    <a href="/support" style="font-size: 14px; font-weight: 400; color: #4A154B; text-decoration: none; margin-left: 24px;">Support</a>
  </div>
</div>
</nav>"""


def _footer_html():
    """Shared footer HTML."""
    return """<footer style="margin-top: 48px; border-top: 1px solid #D1D5DB; padding: 24px 0;">
<div style="text-align: center;">
  <a href="/privacy" style="font-size: 14px; color: #6B7280; text-decoration: none;">Privacy</a>
  <span style="color: #6B7280; margin: 0 8px;">&middot;</span>
  <a href="/support" style="font-size: 14px; color: #6B7280; text-decoration: none;">Support</a>
</div>
</footer>"""


def _landing_page():
    """Render landing page HTML."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LunchBot - Decide where to eat, together</title>
<style>
body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #FFFFFF; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
{_nav_html()}
<div style="max-width: 720px; margin: 0 auto; padding: 0 16px;">
  <div style="padding-top: 64px; padding-bottom: 48px;">
    <h1 style="font-size: 32px; font-weight: 600; color: #111827; line-height: 1.2; margin: 0 0 16px;">Decide where to eat, together</h1>
    <p style="font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5; margin: 0 0 24px;">LunchBot posts a restaurant poll in your Slack channel. Your team votes, you eat. No more endless debates.</p>
    <a href="/slack/install">
      <img alt="Add to Slack" height="40" width="139"
           src="https://platform.slack-edge.com/img/add_to_slack.png"
           srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x">
    </a>
  </div>
  <div style="margin-top: 48px; background: #F9FAFB; border-radius: 8px; padding: 32px 24px;">
    <h2 style="font-size: 20px; font-weight: 600; color: #111827; line-height: 1.2; margin: 0 0 24px;">How it works</h2>
    <div style="margin-bottom: 20px;">
      <div style="font-size: 14px; font-weight: 400; color: #374151; margin-bottom: 4px;">1. Install</div>
      <div style="font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5;">Add LunchBot to your Slack workspace with one click.</div>
    </div>
    <div style="margin-bottom: 20px;">
      <div style="font-size: 14px; font-weight: 400; color: #374151; margin-bottom: 4px;">2. Poll</div>
      <div style="font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5;">Run /lunch and a restaurant poll appears in your channel.</div>
    </div>
    <div>
      <div style="font-size: 14px; font-weight: 400; color: #374151; margin-bottom: 4px;">3. Vote</div>
      <div style="font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5;">Your team picks their favorite. Lunch is decided.</div>
    </div>
  </div>
  {_footer_html()}
</div>
</body>
</html>"""


def _privacy_page():
    """Render privacy policy page HTML."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Privacy Policy - LunchBot</title>
<style>
body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #FFFFFF; }}
a {{ color: #4A154B; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
{_nav_html()}
<div style="max-width: 640px; margin: 0 auto; padding: 0 16px;">
  <h1 style="font-size: 20px; font-weight: 600; color: #111827; line-height: 1.2; margin: 32px 0 8px;">Privacy Policy</h1>
  <p style="font-size: 14px; color: #6B7280; margin: 0 0 24px;">Last updated: April 2026</p>

  <h2 style="font-size: 14px; font-weight: 400; color: #111827; margin: 24px 0 8px;">What LunchBot Does</h2>
  <p style="font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5; margin: 0 0 16px;">LunchBot is a Slack bot that helps teams decide where to eat lunch by posting restaurant polls in Slack channels.</p>

  <h2 style="font-size: 14px; font-weight: 400; color: #111827; margin: 24px 0 8px;">Data We Collect</h2>
  <ul style="font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5; margin: 0 0 16px; padding-left: 20px;">
    <li style="margin-bottom: 8px;">Workspace ID and team name (stored in database)</li>
    <li style="margin-bottom: 8px;">User display names and avatar URLs (cached in memory during active sessions, not persisted to database)</li>
    <li style="margin-bottom: 8px;">Vote history including user ID and restaurant selections (stored in database)</li>
    <li style="margin-bottom: 8px;">Encrypted bot token (Fernet-encrypted, stored in database)</li>
    <li>Restaurant data from Google Places API: name, address, rating, place ID (cached in database)</li>
  </ul>

  <h2 style="font-size: 14px; font-weight: 400; color: #111827; margin: 24px 0 8px;">How We Use Your Data</h2>
  <p style="font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5; margin: 0 0 16px;">We use your data solely to operate the lunch poll service. We do not use your data for advertising. We do not sell your data to third parties.</p>

  <h2 style="font-size: 14px; font-weight: 400; color: #111827; margin: 24px 0 8px;">Data Retention</h2>
  <p style="font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5; margin: 0 0 16px;">Your data is retained while LunchBot is installed in your workspace. After uninstall, your workspace is soft-deleted: tokens are cleared and the workspace is marked inactive. Historical vote data is not automatically purged.</p>

  <h2 style="font-size: 14px; font-weight: 400; color: #111827; margin: 24px 0 8px;">Data Deletion</h2>
  <p style="font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5; margin: 0 0 16px;">Uninstalling LunchBot from your Slack workspace triggers automatic soft-deletion of your workspace data. For full data removal requests, contact <a href="mailto:support@lunchbot.app">support@lunchbot.app</a>.</p>

  <h2 style="font-size: 14px; font-weight: 400; color: #111827; margin: 24px 0 8px;">Third-Party Services</h2>
  <p style="font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5; margin: 0 0 8px;">LunchBot uses the following third-party services:</p>
  <ul style="font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5; margin: 0 0 16px; padding-left: 20px;">
    <li style="margin-bottom: 8px;">Google Places API (<a href="https://policies.google.com/privacy">Google Privacy Policy</a>)</li>
    <li>Slack API (<a href="https://slack.com/privacy-policy">Slack Privacy Policy</a>)</li>
  </ul>

  <h2 style="font-size: 14px; font-weight: 400; color: #111827; margin: 24px 0 8px;">Contact</h2>
  <p style="font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5; margin: 0 0 16px;">Questions about this policy? Email <a href="mailto:support@lunchbot.app">support@lunchbot.app</a>.</p>

  {_footer_html()}
</div>
</body>
</html>"""


def _support_page():
    """Render support page HTML."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Support - LunchBot</title>
<style>
body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 0; background: #FFFFFF; }}
a {{ color: #4A154B; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
{_nav_html()}
<div style="max-width: 480px; margin: 0 auto; padding: 0 16px;">
  <h1 style="font-size: 20px; font-weight: 600; color: #111827; line-height: 1.2; margin: 32px 0 16px;">Support</h1>
  <p style="font-size: 16px; font-weight: 400; color: #374151; line-height: 1.5; margin: 0 0 16px;">Have a question or running into a problem? Email us at <a href="mailto:support@lunchbot.app">support@lunchbot.app</a> and we'll get back to you within 2 business days.</p>
  {_footer_html()}
</div>
</body>
</html>"""


@bp.route('/')
def landing():
    """Landing page with Add to Slack button."""
    return _landing_page()


@bp.route('/privacy')
def privacy():
    """Privacy policy page."""
    return _privacy_page()


@bp.route('/support')
def support():
    """Support contact page."""
    return _support_page()
