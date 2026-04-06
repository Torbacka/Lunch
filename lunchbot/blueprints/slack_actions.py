"""Slack interactive action endpoints.

Handles: /action (vote clicks, suggestion select, App Home buttons, modal submissions),
         /find_suggestions (external select search).
"""
import json
import structlog
from datetime import date, time

from flask import Blueprint, current_app, request, jsonify, g

from lunchbot.client import places_client, db_client
from lunchbot.client.workspace_client import get_workspace, get_workspace_settings, update_workspace_settings
from lunchbot.client import slack_client
from lunchbot.services import vote_service
from lunchbot.services.app_home_service import (
    build_home_view, build_channel_modal, build_schedule_modal,
    build_poll_size_modal, build_location_modal, build_remove_schedule_modal,
    ACTION_BEGIN_SETUP, ACTION_EDIT_CHANNEL, ACTION_EDIT_SCHEDULE,
    ACTION_EDIT_POLL_SIZE, ACTION_EDIT_LOCATION, ACTION_REMOVE_SCHEDULE,
    CALLBACK_CHANNEL, CALLBACK_SCHEDULE, CALLBACK_POLL_SIZE,
    CALLBACK_LOCATION, CALLBACK_REMOVE_SCHEDULE,
)
from lunchbot.services.scheduler_service import update_schedule_job, remove_schedule_job

logger = structlog.get_logger(__name__)

bp = Blueprint('slack_actions', __name__)

# App Home action IDs for dispatch
_APP_HOME_ACTIONS = frozenset({
    ACTION_BEGIN_SETUP, ACTION_EDIT_CHANNEL, ACTION_EDIT_SCHEDULE,
    ACTION_EDIT_POLL_SIZE, ACTION_EDIT_LOCATION, ACTION_REMOVE_SCHEDULE,
})


def suggest(place_id):
    """Add a restaurant as a poll option for today.

    Fetches restaurant from DB by place_id. If url is missing, fetches
    details from Google Places API and updates the restaurant record.
    Then upserts a poll option for today.
    T-03-17: place_id used in parameterized SQL only.
    """
    restaurant = db_client.get_restaurant_by_place_id(place_id)
    if restaurant and not restaurant.get('url'):
        details = places_client.get_details(place_id)
        result = details.get('result', {})
        db_client.update_restaurant_url(
            place_id,
            result.get('url', ''),
            result.get('website', ''),
        )
    if restaurant:
        db_client.upsert_suggestion(date.today(), restaurant['id'])


@bp.route('/action', methods=['POST'])
def action():
    """Handle Slack interactive actions (button clicks, modal submissions, external selects).

    Dispatches on payload type:
    - view_submission: modal form submissions (App Home settings)
    - block_actions: button clicks (App Home edit buttons, vote buttons)
    T-03-07: int() cast in vote_service catches malformed poll_option_id.
    T-05-08: All payloads verified by Slack signature middleware.
    """
    payload = json.loads(request.form.get('payload', '{}'))
    payload_type = payload.get('type')
    logger.info('slack_action_received', payload_type=payload_type)

    if payload_type == 'view_submission':
        return _handle_view_submission(payload)
    elif payload_type == 'block_actions':
        return _handle_block_actions(payload)

    return '', 200


def _handle_block_actions(payload):
    """Handle button clicks from App Home and existing vote/suggest actions."""
    actions = payload.get('actions', [])
    if not actions:
        return '', 200

    first_action = actions[0]
    action_id = first_action.get('action_id', '')
    team_id = payload.get('team', {}).get('id') or getattr(g, 'workspace_id', None)
    trigger_id = payload.get('trigger_id')

    # App Home button actions
    if action_id in _APP_HOME_ACTIONS:
        return _handle_app_home_action(action_id, team_id, trigger_id)

    # Legacy: existing vote/suggest handling
    return _handle_legacy_action(payload, first_action)


def _handle_app_home_action(action_id, team_id, trigger_id):
    """Handle App Home button clicks by opening the appropriate modal."""
    if action_id in (ACTION_BEGIN_SETUP, ACTION_EDIT_CHANNEL):
        settings = get_workspace_settings(team_id)
        modal = build_channel_modal(
            current_channel=settings.get('poll_channel') if settings else None,
            team_id=team_id,
        )
        slack_client.views_open(trigger_id, modal, team_id)
        return '', 200

    if action_id == ACTION_EDIT_SCHEDULE:
        settings = get_workspace_settings(team_id)
        modal = build_schedule_modal(
            current_time=settings.get('poll_schedule_time') if settings else None,
            current_tz=settings.get('poll_schedule_timezone') if settings else None,
            current_days=settings.get('poll_schedule_weekdays') if settings else None,
            team_id=team_id,
        )
        slack_client.views_open(trigger_id, modal, team_id)
        return '', 200

    if action_id == ACTION_EDIT_POLL_SIZE:
        settings = get_workspace_settings(team_id)
        modal = build_poll_size_modal(
            current_size=settings.get('poll_size') if settings else None,
            current_smart=settings.get('smart_picks') if settings else None,
            team_id=team_id,
        )
        slack_client.views_open(trigger_id, modal, team_id)
        return '', 200

    if action_id == ACTION_EDIT_LOCATION:
        settings = get_workspace_settings(team_id)
        modal = build_location_modal(
            current_location=settings.get('location') if settings else None,
            team_id=team_id,
        )
        slack_client.views_open(trigger_id, modal, team_id)
        return '', 200

    if action_id == ACTION_REMOVE_SCHEDULE:
        modal = build_remove_schedule_modal(team_id=team_id)
        slack_client.views_open(trigger_id, modal, team_id)
        return '', 200

    return '', 200


def _handle_legacy_action(payload, first_action):
    """Handle existing vote and suggestion actions (pre-Phase 5 logic)."""
    action_type = first_action.get('type')
    if action_type == 'button':
        logger.info('vote_received', poll_option_id=first_action.get('value'))
        vote_service.vote(payload)
        try:
            workspace_id = payload.get('team', {}).get('id', 'unknown')
            current_app.extensions['prom_votes_cast'].labels(workspace_id=workspace_id).inc()
        except (KeyError, RuntimeError):
            pass  # metrics not initialized or outside app context
    elif action_type == 'external_select':
        selected = first_action.get('selected_option', {})
        place_id = selected.get('value', '')
        logger.info('suggestion_selected', place_id=place_id)
        suggest(place_id)
    return '', 200


def _handle_view_submission(payload):
    """Handle modal form submissions from App Home settings modals."""
    callback_id = payload.get('view', {}).get('callback_id', '')
    private_metadata = json.loads(payload.get('view', {}).get('private_metadata', '{}'))
    team_id = private_metadata.get('team_id')
    user_id = payload.get('user', {}).get('id')
    logger.info('modal_submitted', callback_id=callback_id, team_id=team_id)
    values = payload.get('view', {}).get('state', {}).get('values', {})

    if not team_id:
        return '', 200

    if callback_id == CALLBACK_CHANNEL:
        channel = _extract_value(values, 'channel_select', 'selected_conversation')
        if channel:
            update_workspace_settings(team_id, poll_channel=channel)
        _refresh_app_home(user_id, team_id)
        return '', 200

    if callback_id == CALLBACK_SCHEDULE:
        time_str = _extract_value(values, 'schedule_time', 'selected_time')
        tz = _extract_value(values, 'schedule_tz', 'selected_option', key='value')
        days_raw = _extract_value(values, 'schedule_days', 'selected_options')
        days = [d['value'] for d in (days_raw or [])]

        if not days:
            return jsonify({
                'response_action': 'errors',
                'errors': {'schedule_days_block': 'Select at least one day.'}
            })

        h, m = (int(x) for x in time_str.split(':'))
        time_val = time(h, m)

        update_workspace_settings(
            team_id,
            poll_schedule_time=time_val,
            poll_schedule_timezone=tz,
            poll_schedule_weekdays=days,
        )
        settings = get_workspace_settings(team_id)
        update_schedule_job(
            team_id, time_val, tz, days,
            channel=settings.get('poll_channel') if settings else None,
        )
        _refresh_app_home(user_id, team_id)
        return '', 200

    if callback_id == CALLBACK_POLL_SIZE:
        total = int(_extract_value(values, 'poll_total', 'selected_option', key='value'))
        smart = int(_extract_value(values, 'smart_count', 'selected_option', key='value'))

        if smart >= total:
            return jsonify({
                'response_action': 'errors',
                'errors': {'smart_count_block': "Smart picks must be fewer than total options, so there's room for new discoveries."}
            })

        update_workspace_settings(team_id, poll_size=total, smart_picks=smart)
        _refresh_app_home(user_id, team_id)
        return '', 200

    if callback_id == CALLBACK_LOCATION:
        loc = _extract_value(values, 'location_input', 'value')
        if not loc or not loc.strip():
            return jsonify({
                'response_action': 'errors',
                'errors': {'location_input_block': 'Location must not be empty.'}
            })
        update_workspace_settings(team_id, location=loc.strip())
        _refresh_app_home(user_id, team_id)
        return '', 200

    if callback_id == CALLBACK_REMOVE_SCHEDULE:
        update_workspace_settings(
            team_id,
            poll_schedule_time=None,
            poll_schedule_timezone=None,
            poll_schedule_weekdays=None,
        )
        remove_schedule_job(team_id)
        _refresh_app_home(user_id, team_id)
        return '', 200

    return '', 200


def _extract_value(values, action_id, field, key=None):
    """Extract a value from Slack view state values.

    values = {block_id: {action_id: {field: value}}}
    Since block_ids may be auto-generated, search all blocks for the action_id.
    """
    for block_values in values.values():
        if action_id in block_values:
            val = block_values[action_id].get(field)
            if key and isinstance(val, dict):
                return val.get(key)
            return val
    return None


def _refresh_app_home(user_id, team_id):
    """Re-publish the App Home after a settings change."""
    if not user_id or not team_id:
        return
    settings = get_workspace_settings(team_id)
    view = build_home_view(settings, is_admin=True)  # Only admins can submit modals
    slack_client.views_publish(user_id, view, team_id)


@bp.route('/find_suggestions', methods=['POST'])
def find_suggestions():
    """Handle Slack external select search for restaurants.

    Parses payload from form field, searches Google Places API,
    caches results in PostgreSQL, and returns formatted Slack options.
    T-03-13: search string passed as Places API keyword, not SQL.
    T-03-15: Slack signature middleware validates request origin.
    """
    payload = json.loads(request.form.get('payload', '{}'))
    search_value = payload.get('value', '')
    logger.info('suggestion_search', search_value=search_value)

    workspace = get_workspace(g.workspace_id)
    location = workspace.get('location') if workspace else None
    if not location:
        return jsonify({'options': []})

    response = places_client.find_suggestion(search_value, location)
    db_client.save_restaurants(response)

    options = []
    for result in response.get('results', []):
        opening_hours = result.get('opening_hours', {})
        open_status = 'open' if opening_hours.get('open_now') else 'closed'
        rating = result.get('rating', '')
        name = result.get('name', '')
        text = f"{name} {open_status} {rating}"
        options.append({
            'text': {'type': 'plain_text', 'text': text},
            'value': result['place_id'],
        })

    return jsonify({'options': options})
