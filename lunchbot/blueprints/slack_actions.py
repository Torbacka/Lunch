"""Slack interactive action endpoints.

Handles: /action (vote clicks, suggestion select, App Home buttons, modal submissions),
         /find_suggestions (external select search).
"""
import json
import structlog
from datetime import date, time

from flask import Blueprint, current_app, request, jsonify, g

from lunchbot.client import places_client, db_client
from lunchbot.client.workspace_client import (
    get_workspace, get_workspace_settings, update_workspace_settings,
    bind_channel_location, resolve_location_for_channel,
    create_workspace_location, list_workspace_locations,
    rename_workspace_location, delete_workspace_location,
    set_default_workspace_location,
)
from lunchbot.client import slack_client
from lunchbot.services import vote_service, poll_service
from lunchbot.blueprints.polls import (
    CHANNEL_LOC_USE_DEFAULT, CHANNEL_LOC_PICK, CHANNEL_LOC_ADD_OFFICE,
)
from lunchbot.services.office_modal_service import (
    build_add_office_modal, CALLBACK_ADD_OFFICE, OFFICE_SEARCH_SELECT,
    OFFICE_SEARCH_BLOCK,
)
from lunchbot.services.app_home_service import (
    build_home_view, build_schedule_channel_modal,
    build_poll_size_modal,
    build_rename_office_modal, build_delete_office_modal,
    ACTION_BEGIN_SETUP,
    ACTION_EDIT_POLL_SIZE,
    ACTION_OPEN_SCHEDULE_CHANNEL_MODAL, ACTION_EDIT_CHANNEL_SCHEDULE,
    ACTION_ADD_OFFICE_FROM_HOME, ACTION_RENAME_OFFICE,
    ACTION_SET_DEFAULT_OFFICE, ACTION_DELETE_OFFICE,
    CALLBACK_SCHEDULE_CHANNEL, CALLBACK_POLL_SIZE,
    CALLBACK_RENAME_OFFICE, CALLBACK_DELETE_OFFICE,
)
from lunchbot.services.scheduler_service import update_schedule_job

logger = structlog.get_logger(__name__)

bp = Blueprint('slack_actions', __name__)

# App Home action IDs for dispatch
_APP_HOME_ACTIONS = frozenset({
    ACTION_BEGIN_SETUP,
    ACTION_EDIT_POLL_SIZE,
    ACTION_OPEN_SCHEDULE_CHANNEL_MODAL, ACTION_EDIT_CHANNEL_SCHEDULE,
    ACTION_ADD_OFFICE_FROM_HOME, ACTION_RENAME_OFFICE,
    ACTION_SET_DEFAULT_OFFICE, ACTION_DELETE_OFFICE,
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
        user_id = payload.get('user', {}).get('id')
        return _handle_app_home_action(
            action_id, team_id, trigger_id, user_id, first_action,
        )

    # Channel-location first-use binding actions
    if action_id in (CHANNEL_LOC_USE_DEFAULT, CHANNEL_LOC_PICK):
        return _handle_channel_location_bind(action_id, payload, first_action)

    # Add-office button opens the places-backed modal
    if action_id == CHANNEL_LOC_ADD_OFFICE:
        channel_id = payload.get('channel', {}).get('id', '')
        modal = build_add_office_modal(team_id, channel_id=channel_id)
        slack_client.views_open(trigger_id, modal, team_id)
        return '', 200

    # Legacy: existing vote/suggest handling
    return _handle_legacy_action(payload, first_action)


def _handle_channel_location_bind(action_id, payload, first_action):
    """Persist the user's office choice for this channel and post the poll."""
    team_id = payload.get('team', {}).get('id', '')
    channel_id = payload.get('channel', {}).get('id', '')

    if action_id == CHANNEL_LOC_USE_DEFAULT:
        raw = first_action.get('value', '')
    else:  # CHANNEL_LOC_PICK
        raw = first_action.get('selected_option', {}).get('value', '')

    try:
        location_id = int(raw)
    except (TypeError, ValueError):
        logger.warning('channel_location_bind_bad_value', value=raw, action_id=action_id)
        return '', 200

    bind_channel_location(team_id, channel_id, location_id)
    logger.info('channel_location_bound', team_id=team_id, channel_id=channel_id,
                location_id=location_id)
    try:
        poll_service.push_poll(channel_id, team_id, trigger_source='channel_bind')
    except ValueError as e:
        logger.warning('push_poll_after_bind_failed', error=str(e))
    return '', 200


def _handle_app_home_action(action_id, team_id, trigger_id, user_id=None, first_action=None):
    """Handle App Home button clicks by opening the appropriate modal."""
    if action_id == ACTION_BEGIN_SETUP:
        # Begin-setup now opens the schedule-channel modal (no workspace-level channel picker)
        channels, _ = slack_client.list_bot_channels(team_id)
        modal = build_schedule_channel_modal(channels, team_id=team_id)
        slack_client.views_open(trigger_id, modal, team_id)
        return '', 200

    if action_id == ACTION_OPEN_SCHEDULE_CHANNEL_MODAL:
        channels, _ = slack_client.list_bot_channels(team_id)
        modal = build_schedule_channel_modal(channels, team_id=team_id)
        slack_client.views_open(trigger_id, modal, team_id)
        return '', 200

    if action_id == ACTION_EDIT_CHANNEL_SCHEDULE:
        channel_id = (first_action or {}).get('value', '')
        existing = db_client.get_channel_schedule(team_id, channel_id)
        channels, _ = slack_client.list_bot_channels(team_id)
        modal = build_schedule_channel_modal(channels, team_id=team_id, existing=existing)
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

    if action_id == ACTION_ADD_OFFICE_FROM_HOME:
        # No admin gate — non-admins are allowed to add offices (D-07/D-15).
        modal = build_add_office_modal(team_id, channel_id=None)
        slack_client.views_open(trigger_id, modal, team_id)
        return '', 200

    if action_id in (
        ACTION_RENAME_OFFICE, ACTION_SET_DEFAULT_OFFICE, ACTION_DELETE_OFFICE,
    ):
        if not slack_client.is_workspace_admin(user_id, team_id):
            logger.warning(
                'app_home_admin_gate_blocked',
                team_id=team_id, user_id=user_id, action_id=action_id,
            )
            return '', 200
        try:
            location_id = int((first_action or {}).get('value', ''))
        except (TypeError, ValueError):
            return '', 200
        rows = list_workspace_locations(team_id) or []
        target = next((r for r in rows if r['id'] == location_id), None)
        if target is None:
            return '', 200

        if action_id == ACTION_RENAME_OFFICE:
            modal = build_rename_office_modal(team_id, location_id, target['name'])
            slack_client.views_open(trigger_id, modal, team_id)
            return '', 200

        if action_id == ACTION_DELETE_OFFICE:
            modal = build_delete_office_modal(team_id, location_id, target['name'])
            slack_client.views_open(trigger_id, modal, team_id)
            return '', 200

        if action_id == ACTION_SET_DEFAULT_OFFICE:
            set_default_workspace_location(team_id, location_id, user_id)
            _refresh_app_home(user_id, team_id)
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

    if callback_id == CALLBACK_SCHEDULE_CHANNEL:
        # Channel from static_select (create) or private_metadata (edit)
        channel_id = _extract_value(values, 'schedule_channel', 'selected_option', key='value')
        if not channel_id:
            channel_id = private_metadata.get('channel_id')
        if not channel_id:
            return jsonify({
                'response_action': 'errors',
                'errors': {'schedule_channel_block': 'Select a channel.'},
            })

        time_str = _extract_value(values, 'schedule_time', 'selected_time')
        tz = _extract_value(values, 'schedule_tz', 'selected_option', key='value')
        days_raw = _extract_value(values, 'schedule_weekdays', 'selected_options')
        days = [d['value'] for d in (days_raw or [])]

        if not days:
            return jsonify({
                'response_action': 'errors',
                'errors': {'schedule_weekdays_block': 'Select at least one day.'},
            })

        h, m = (int(x) for x in time_str.split(':'))
        time_val = time(h, m)
        weekdays_str = ','.join(days)

        db_client.upsert_channel_schedule(team_id, channel_id, time_val, tz, weekdays_str)
        update_schedule_job(team_id, channel_id, time_val, tz, days)
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

    if callback_id == CALLBACK_RENAME_OFFICE:
        if not slack_client.is_workspace_admin(user_id, team_id):
            return jsonify({
                'response_action': 'errors',
                'errors': {
                    'office_name_block': 'Only workspace admins can rename offices.',
                },
            })
        location_id = private_metadata.get('location_id')
        new_name = _extract_value(values, 'office_name_input', 'value')
        if not new_name or not new_name.strip():
            return jsonify({
                'response_action': 'errors',
                'errors': {'office_name_block': 'Name must not be empty.'},
            })
        rename_workspace_location(
            team_id, int(location_id), new_name.strip(), user_id,
        )
        _refresh_app_home(user_id, team_id)
        return '', 200

    if callback_id == CALLBACK_DELETE_OFFICE:
        if not slack_client.is_workspace_admin(user_id, team_id):
            # Silent close on non-admin attempts (defense in depth).
            return jsonify({'response_action': 'errors', 'errors': {}})
        location_id = private_metadata.get('location_id')
        delete_workspace_location(team_id, int(location_id), user_id)
        _refresh_app_home(user_id, team_id)
        return '', 200

    if callback_id == CALLBACK_ADD_OFFICE:
        channel_id = private_metadata.get('channel_id')
        place_id = _extract_value(
            values, OFFICE_SEARCH_SELECT, 'selected_option', key='value',
        )
        if not place_id:
            return jsonify({
                'response_action': 'errors',
                'errors': {OFFICE_SEARCH_BLOCK: 'Pick an address from the search results.'},
            })
        details = places_client.get_place_details(place_id)
        result = (details or {}).get('result') or {}
        loc = (result.get('geometry') or {}).get('location') or {}
        if 'lat' not in loc or 'lng' not in loc:
            return jsonify({
                'response_action': 'errors',
                'errors': {OFFICE_SEARCH_BLOCK: 'Could not resolve that address. Try another.'},
            })
        name = result.get('name') or 'Office'
        formatted = result.get('formatted_address') or ''
        short = formatted.split(',', 1)[0].strip() if formatted else ''
        office_name = f'{name}, {short}' if short and short.lower() != name.lower() else name
        lat_lng = f"{loc['lat']},{loc['lng']}"

        existing = list_workspace_locations(team_id) or []
        is_first = len(existing) == 0
        row = create_workspace_location(team_id, office_name, lat_lng, is_default=is_first)
        via = 'lunch_prompt' if channel_id else 'app_home'
        logger.info(
            'office_create',
            team_id=team_id, location_id=row['id'],
            actor_user_id=user_id, via=via,
        )

        if channel_id:
            bind_channel_location(team_id, channel_id, row['id'])
            try:
                poll_service.push_poll(channel_id, team_id, trigger_source='add_office_modal')
            except ValueError as e:
                logger.warning('push_poll_after_add_office_failed', error=str(e))
        else:
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
    locations = list_workspace_locations(team_id) or []
    schedules = db_client.list_channel_schedules(team_id)
    is_admin = slack_client.is_workspace_admin(user_id, team_id)
    view = build_home_view(settings, is_admin=is_admin, locations=locations, schedules=schedules)
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

    # Office search (Add-office modal) is a Places Autocomplete proxy and does
    # NOT depend on a bound channel.
    action_id = payload.get('action_id', '')
    if action_id == OFFICE_SEARCH_SELECT:
        token = places_client.new_session_token()
        data = places_client.autocomplete(search_value, session_token=token) if search_value else {}
        options = []
        for p in (data.get('predictions') or [])[:20]:
            options.append({
                'text': {'type': 'plain_text', 'text': (p.get('description') or '')[:75]},
                'value': p.get('place_id'),
            })
        return jsonify({'options': options})

    # Resolve location via the channel binding (not the deprecated
    # workspaces.location column). The external_select payload carries the
    # channel id the user is interacting from.
    channel_id = payload.get('channel', {}).get('id', '')
    location_row = resolve_location_for_channel(g.workspace_id, channel_id) if channel_id else None
    location = location_row.get('lat_lng') if location_row else None
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
