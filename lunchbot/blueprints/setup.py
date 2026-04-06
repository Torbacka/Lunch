"""Workspace setup flow.

After OAuth installation, the admin is redirected here to configure
their office location. On submit, restaurants are seeded in the background.

Endpoints:
  GET  /slack/setup  -- show location form
  POST /slack/setup  -- save location, trigger background seed
"""
import logging
import threading

from flask import Blueprint, request, current_app

from lunchbot.client.workspace_client import get_workspace, update_workspace_location
from lunchbot.services import emoji_service

logger = logging.getLogger(__name__)

bp = Blueprint('setup', __name__, url_prefix='/slack')


def _seed_restaurants(app, team_id, location):
    """Run restaurant seeding inside a pushed app context."""
    with app.app_context():
        logger.info('Background seed started for team_id=%s location=%s', team_id, location)
        try:
            emoji_service.search_and_update_emoji(location)
            logger.info('Background seed complete for team_id=%s', team_id)
        except Exception:
            logger.exception('Background seed failed for team_id=%s', team_id)


@bp.route('/setup', methods=['GET'])
def setup_form():
    """Show location setup form after OAuth installation."""
    team_id = request.args.get('team_id', '')
    return _form_page(team_id)


@bp.route('/setup', methods=['POST'])
def setup_submit():
    """Save workspace location and trigger background restaurant seeding."""
    team_id = request.form.get('team_id', '').strip()
    lat = request.form.get('lat', '').strip()
    lng = request.form.get('lng', '').strip()

    if not team_id or not lat or not lng:
        return _form_page(team_id, error='All fields are required.'), 400

    try:
        float(lat)
        float(lng)
    except ValueError:
        return _form_page(team_id, error='Latitude and longitude must be numbers.'), 400

    workspace = get_workspace(team_id)
    if not workspace:
        logger.warning('Setup submitted for unknown team_id=%s', team_id)
        return _form_page(team_id, error='Workspace not found. Please reinstall LunchBot.'), 400

    location = f'{lat},{lng}'
    update_workspace_location(team_id, location)
    logger.info('Location saved for team_id=%s: %s', team_id, location)

    app = current_app._get_current_object()
    thread = threading.Thread(
        target=_seed_restaurants,
        args=(app, team_id, location),
        daemon=True,
    )
    thread.start()

    return _success_page()


def _form_page(team_id, error=None):
    error_html = f'<p class="error">{error}</p>' if error else ''
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LunchBot Setup</title>
<style>
body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 16px; background: #FFFFFF; }}
.content {{ max-width: 480px; margin: 24px auto 0; }}
h1 {{ font-size: 20px; font-weight: 600; color: #111827; margin: 0 0 8px; }}
p {{ font-size: 15px; color: #374151; line-height: 1.5; margin: 0 0 16px; }}
label {{ display: block; font-size: 14px; font-weight: 500; color: #111827; margin-bottom: 4px; }}
input {{ width: 100%; box-sizing: border-box; padding: 8px 10px; font-size: 15px; border: 1px solid #D1D5DB; border-radius: 6px; margin-bottom: 12px; }}
button {{ background: #4A154B; color: #fff; border: none; padding: 10px 20px; font-size: 15px; font-weight: 500; border-radius: 6px; cursor: pointer; }}
button:hover {{ background: #3b1040; }}
.hint {{ font-size: 13px; color: #6B7280; margin-top: -8px; margin-bottom: 12px; }}
.error {{ color: #DC2626; font-size: 14px; margin-bottom: 12px; }}
</style>
</head>
<body>
<div class="content">
<h1>Set up LunchBot</h1>
<p>Enter your office coordinates so LunchBot can find nearby restaurants.</p>
<p class="hint">Tip: right-click your office in <a href="https://maps.google.com" target="_blank">Google Maps</a> to copy the coordinates.</p>
{error_html}
<form method="POST" action="/slack/setup">
  <input type="hidden" name="team_id" value="{team_id}">
  <label for="lat">Latitude</label>
  <input type="text" id="lat" name="lat" placeholder="59.3419128" required>
  <label for="lng">Longitude</label>
  <input type="text" id="lng" name="lng" placeholder="18.0644956" required>
  <button type="submit">Save &amp; find restaurants</button>
</form>
</div>
</body>
</html>"""


def _success_page():
    return """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LunchBot Ready</title>
<style>
body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 16px; background: #FFFFFF; }
.content { max-width: 480px; margin: 24px auto 0; }
h1 { font-size: 20px; font-weight: 600; color: #111827; margin: 0 0 16px; }
p { font-size: 16px; color: #374151; line-height: 1.5; margin: 0 0 16px; }
a { color: #4A154B; text-decoration: none; }
a:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="content">
<h1>LunchBot is ready!</h1>
<p>We're loading nearby restaurants in the background. This takes about a minute.</p>
<p>Go back to Slack and run <strong>/lunch</strong> to post a poll.</p>
<a href="https://slack.com">Return to Slack</a>
</div>
</body>
</html>"""
