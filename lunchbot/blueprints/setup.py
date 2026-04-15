"""Workspace setup flow.

After OAuth installation, the admin picks their office via Google Places
Autocomplete and a workspace_locations row is created. Restaurants are seeded
in the background.

Endpoints:
  GET  /slack/setup  -- show Places-autocomplete form
  POST /slack/setup  -- resolve place_id, create office, trigger background seed
"""
import logging
import threading

import structlog
from flask import Blueprint, request, current_app, g

from lunchbot.client import places_client
from lunchbot.client.workspace_client import get_workspace, create_workspace_location
from lunchbot.services import emoji_service

logger = structlog.get_logger(__name__)
_legacy_logger = logging.getLogger(__name__)

bp = Blueprint('setup', __name__, url_prefix='/slack')


def _seed_restaurants(app, team_id, location):
    """Run restaurant seeding inside a pushed app context."""
    with app.app_context():
        g.workspace_id = team_id
        _legacy_logger.info('Background seed started for team_id=%s location=%s', team_id, location)
        try:
            emoji_service.search_and_update_emoji(location)
            _legacy_logger.info('Background seed complete for team_id=%s', team_id)
        except Exception:
            _legacy_logger.exception('Background seed failed for team_id=%s', team_id)


@bp.route('/setup', methods=['GET'])
def setup_form():
    """Show Places-autocomplete setup form after OAuth installation."""
    team_id = request.args.get('team_id', '')
    return _form_page(team_id)


@bp.route('/setup', methods=['POST'])
def setup_submit():
    """Resolve the chosen place_id, create a workspace_locations row, kick off seeding."""
    team_id = request.form.get('team_id', '').strip()
    place_id = request.form.get('place_id', '').strip()
    session_token = request.form.get('session_token', '').strip() or None

    if not team_id or not place_id:
        return _form_page(team_id, error='Pick an address from the suggestions.'), 400

    workspace = get_workspace(team_id)
    if not workspace:
        logger.warning('setup_unknown_team', team_id=team_id)
        return _form_page(team_id, error='Workspace not found. Please reinstall LunchBot.'), 400

    details = places_client.get_place_details(place_id, session_token=session_token)
    result = (details or {}).get('result') or {}
    loc = (result.get('geometry') or {}).get('location') or {}
    lat = loc.get('lat')
    lng = loc.get('lng')
    if lat is None or lng is None:
        logger.warning('setup_place_resolve_failed', team_id=team_id, place_id=place_id)
        return _form_page(team_id, error='Could not resolve that address. Try a different one.'), 400

    name = result.get('name') or 'Office'
    formatted = result.get('formatted_address') or ''
    short = formatted.split(',', 1)[0].strip() if formatted else ''
    office_name = f'{name}, {short}' if short and short.lower() != name.lower() else name

    lat_lng = f'{lat},{lng}'
    row = create_workspace_location(team_id, office_name, lat_lng, is_default=True)
    logger.info(
        'office_create',
        team_id=team_id,
        location_id=row['id'],
        actor_user_id='install',
        via='install_flow',
        place_id=place_id,
    )

    app = current_app._get_current_object()
    thread = threading.Thread(
        target=_seed_restaurants,
        args=(app, team_id, lat_lng),
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
input[type=text] {{ width: 100%; box-sizing: border-box; padding: 8px 10px; font-size: 15px; border: 1px solid #D1D5DB; border-radius: 6px; }}
button {{ background: #4A154B; color: #fff; border: none; padding: 10px 20px; font-size: 15px; font-weight: 500; border-radius: 6px; cursor: pointer; margin-top: 12px; }}
button[disabled] {{ background: #9CA3AF; cursor: not-allowed; }}
button:hover:not([disabled]) {{ background: #3b1040; }}
.suggestions {{ border: 1px solid #D1D5DB; border-top: none; border-radius: 0 0 6px 6px; max-height: 240px; overflow-y: auto; background: #fff; }}
.suggestion {{ padding: 8px 10px; cursor: pointer; font-size: 14px; }}
.suggestion:hover {{ background: #F3F4F6; }}
.suggestion .secondary {{ color: #6B7280; font-size: 12px; }}
.error {{ color: #DC2626; font-size: 14px; margin-bottom: 12px; }}
.selected {{ font-size: 13px; color: #047857; margin-top: 4px; min-height: 18px; }}
</style>
</head>
<body>
<div class="content">
<h1>Set up LunchBot</h1>
<p>Search for your office address. LunchBot will use it to find nearby restaurants.</p>
{error_html}
<form method="POST" action="/slack/setup" id="setup-form">
  <input type="hidden" name="team_id" value="{team_id}">
  <input type="hidden" name="place_id" id="place_id" value="">
  <input type="hidden" name="session_token" id="session_token" value="">
  <label for="address">Office address</label>
  <input type="text" id="address" autocomplete="off" placeholder="e.g. Spotify HQ, Stockholm" required>
  <div class="suggestions" id="suggestions" hidden></div>
  <div class="selected" id="selected"></div>
  <button type="submit" id="submit-btn" disabled>Save &amp; find restaurants</button>
</form>
</div>
<script>
(function() {{
  var input = document.getElementById('address');
  var box = document.getElementById('suggestions');
  var hidden = document.getElementById('place_id');
  var tokenField = document.getElementById('session_token');
  var selected = document.getElementById('selected');
  var btn = document.getElementById('submit-btn');
  var sessionToken = '';
  var debounce = null;

  function clearSuggestions() {{ box.innerHTML = ''; box.hidden = true; }}

  input.addEventListener('input', function() {{
    hidden.value = '';
    selected.textContent = '';
    btn.disabled = true;
    var q = input.value.trim();
    if (q.length < 3) {{ clearSuggestions(); return; }}
    clearTimeout(debounce);
    debounce = setTimeout(function() {{
      var url = '/places/autocomplete?q=' + encodeURIComponent(q);
      if (sessionToken) url += '&session_token=' + encodeURIComponent(sessionToken);
      fetch(url).then(function(r) {{ return r.json(); }}).then(function(data) {{
        if (data.session_token) {{ sessionToken = data.session_token; tokenField.value = sessionToken; }}
        box.innerHTML = '';
        (data.predictions || []).forEach(function(p) {{
          var div = document.createElement('div');
          div.className = 'suggestion';
          div.innerHTML = '<div>' + (p.main_text || p.description) + '</div>' +
                          '<div class="secondary">' + (p.secondary_text || '') + '</div>';
          div.addEventListener('click', function() {{
            input.value = p.description;
            hidden.value = p.place_id;
            selected.textContent = 'Selected: ' + p.description;
            btn.disabled = false;
            clearSuggestions();
          }});
          box.appendChild(div);
        }});
        box.hidden = box.children.length === 0;
      }}).catch(function() {{ clearSuggestions(); }});
    }}, 250);
  }});

  document.addEventListener('click', function(e) {{
    if (!box.contains(e.target) && e.target !== input) clearSuggestions();
  }});
}})();
</script>
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
