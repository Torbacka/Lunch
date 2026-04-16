"""App Home Block Kit builders for settings panel and configuration modals.

Builds all Slack Block Kit views for the App Home tab per 05-UI-SPEC.md.
Each function returns a dict ready to pass to views.publish or views.open.
"""
import json

# Action IDs for button clicks
ACTION_BEGIN_SETUP = 'app_home_begin_setup'
ACTION_EDIT_POLL_SIZE = 'app_home_edit_poll_size'

# Per-channel schedule action IDs (Phase 07.2 Plan 06)
ACTION_OPEN_SCHEDULE_CHANNEL_MODAL = 'open_schedule_channel_modal'
ACTION_EDIT_CHANNEL_SCHEDULE = 'edit_channel_schedule'

# Offices section action IDs (Phase 07.1 Plan 06)
ACTION_ADD_OFFICE_FROM_HOME = 'app_home_add_office'
ACTION_RENAME_OFFICE = 'app_home_rename_office'
ACTION_SET_DEFAULT_OFFICE = 'app_home_set_default_office'
ACTION_DELETE_OFFICE = 'app_home_delete_office'

# Callback IDs for modal submissions
CALLBACK_SCHEDULE_CHANNEL = 'schedule_channel_modal'
CALLBACK_POLL_SIZE = 'modal_poll_size'
CALLBACK_RENAME_OFFICE = 'modal_rename_office'
CALLBACK_DELETE_OFFICE = 'modal_delete_office'

TIMEZONE_OPTIONS = [
    # Americas
    'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
    'America/Toronto', 'America/Sao_Paulo', 'America/Mexico_City',
    # Europe
    'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Stockholm',
    'Europe/Amsterdam', 'Europe/Madrid', 'Europe/Rome', 'Europe/Warsaw', 'Europe/Moscow',
    # Asia
    'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Kolkata', 'Asia/Singapore',
    'Asia/Dubai', 'Asia/Seoul', 'Asia/Bangkok', 'Asia/Jakarta',
    # Pacific
    'Australia/Sydney', 'Australia/Melbourne', 'Pacific/Auckland', 'Pacific/Honolulu',
    # Africa
    'Africa/Cairo', 'Africa/Lagos',
]

WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

DEFAULT_POLL_SIZE = 5
DEFAULT_SMART_PICKS = 2


def _format_time_12h(t):
    """Format a datetime.time as '11:30 AM' style string."""
    hour = t.hour
    minute = t.minute
    ampm = 'AM' if hour < 12 else 'PM'
    display_hour = hour % 12
    if display_hour == 0:
        display_hour = 12
    return f'{display_hour}:{minute:02d} {ampm}'


def build_home_view(settings, is_admin=True, locations=None, schedules=None):
    """Build the App Home tab view.

    Args:
        settings: dict from get_workspace_settings(), or None for fresh workspace
        is_admin: whether the viewing user is a workspace admin
        locations: list of workspace_location rows (as from list_workspace_locations)
                   or None. Caller is responsible for fetching; this module stays
                   DB-free.
        schedules: list of channel_schedule dicts from list_channel_schedules,
                   or None. Each dict has channel_id, schedule_time,
                   schedule_timezone, schedule_weekdays.

    Returns:
        dict with type 'home' and blocks list
    """
    is_configured = settings is not None
    locations = locations or []
    schedules = schedules or []

    if is_configured:
        blocks = _build_state_b(settings, is_admin, locations, schedules)
    else:
        blocks = _build_state_a(is_admin)

    return {'type': 'home', 'blocks': blocks}


def _build_state_a(is_admin):
    """State A: first-time install, no channel configured."""
    blocks = [
        {'type': 'header', 'text': {'type': 'plain_text', 'text': 'LunchBot Settings'}},
        {'type': 'divider'},
        {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': ':wave: *Welcome to LunchBot!*\nSet up your workspace to get started with lunch polls.',
            },
        },
    ]

    if is_admin:
        blocks.append({
            'type': 'actions',
            'elements': [{
                'type': 'button',
                'text': {'type': 'plain_text', 'text': 'Begin Setup'},
                'action_id': ACTION_BEGIN_SETUP,
                'style': 'primary',
            }],
        })

    blocks.append({'type': 'divider'})
    blocks.append({
        'type': 'context',
        'elements': [{'type': 'mrkdwn', 'text': 'Only workspace admins can change these settings.'}],
    })

    return blocks


def _build_state_b(settings, is_admin, locations=None, schedules=None):
    """State B: configured workspace."""
    locations = locations or []
    schedules = schedules or []
    blocks = [
        {'type': 'header', 'text': {'type': 'plain_text', 'text': 'LunchBot Settings'}},
        {'type': 'divider'},
    ]

    # Per-channel schedule list (replaces legacy Poll Channel + Poll Schedule)
    blocks.extend(_build_channel_schedules_section(schedules, is_admin))
    blocks.append({'type': 'divider'})

    # Poll Size row
    poll_size = settings.get('poll_size') or DEFAULT_POLL_SIZE
    smart_picks = settings.get('smart_picks') if settings.get('smart_picks') is not None else DEFAULT_SMART_PICKS
    random_count = poll_size - smart_picks
    poll_size_section = {
        'type': 'section',
        'text': {
            'type': 'mrkdwn',
            'text': f':bar_chart: *Poll Size*\n{poll_size} options ({smart_picks} smart picks, {random_count} random)',
        },
    }
    if is_admin:
        poll_size_section['accessory'] = {
            'type': 'button',
            'text': {'type': 'plain_text', 'text': 'Edit'},
            'action_id': ACTION_EDIT_POLL_SIZE,
        }
    blocks.append(poll_size_section)
    blocks.append({'type': 'divider'})

    # Offices section (Phase 07.1 Plan 06) — replaces legacy Location row
    blocks.extend(_build_offices_section(locations, is_admin))
    blocks.append({'type': 'divider'})

    # Footer
    if is_admin:
        footer_text = 'Only workspace admins can change these settings.'
    else:
        footer_text = 'Contact a workspace admin to change settings.'
    blocks.append({
        'type': 'context',
        'elements': [{'type': 'mrkdwn', 'text': footer_text}],
    })

    return blocks


def build_schedule_channel_modal(channels, team_id=None, existing=None):
    """Build the per-channel schedule modal (D-14, D-16).

    Args:
        channels: list of dicts with 'id' and 'name' (from list_bot_channels)
        team_id: workspace team ID for private_metadata
        existing: existing channel_schedule dict for edit mode, or None for create

    Returns:
        Modal view dict
    """
    private_meta = {'team_id': team_id}
    modal_blocks = []

    if existing:
        # Edit mode: show channel as read-only text, store channel_id in metadata
        private_meta['channel_id'] = existing['channel_id']
        channel_name = existing.get('channel_name', existing['channel_id'])
        modal_blocks.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f':hash: *Channel:* <#{existing["channel_id"]}>',
            },
        })
    else:
        # Create mode: channel picker
        channel_options = [
            {
                'text': {'type': 'plain_text', 'text': f'#{ch["name"]}'},
                'value': ch['id'],
            }
            for ch in channels
        ]
        if not channel_options:
            channel_options = [
                {'text': {'type': 'plain_text', 'text': 'No channels'}, 'value': '_none_'},
            ]
        modal_blocks.append({
            'type': 'input',
            'block_id': 'schedule_channel_block',
            'label': {'type': 'plain_text', 'text': 'Channel'},
            'element': {
                'type': 'static_select',
                'action_id': 'schedule_channel',
                'placeholder': {'type': 'plain_text', 'text': 'Select a channel'},
                'options': channel_options,
            },
        })

    # Time picker
    time_element = {
        'type': 'timepicker',
        'action_id': 'schedule_time',
        'placeholder': {'type': 'plain_text', 'text': 'Select time'},
    }
    if existing and existing.get('schedule_time') and hasattr(existing['schedule_time'], 'hour'):
        t = existing['schedule_time']
        time_element['initial_time'] = f'{t.hour:02d}:{t.minute:02d}'
    else:
        time_element['initial_time'] = '11:30'

    modal_blocks.append({
        'type': 'input',
        'block_id': 'schedule_time_block',
        'label': {'type': 'plain_text', 'text': 'Time'},
        'element': time_element,
    })

    # Timezone select
    tz_options = [
        {'text': {'type': 'plain_text', 'text': tz}, 'value': tz}
        for tz in TIMEZONE_OPTIONS
    ]
    initial_tz = (existing or {}).get('schedule_timezone') or 'Europe/Stockholm'
    modal_blocks.append({
        'type': 'input',
        'block_id': 'schedule_tz_block',
        'label': {'type': 'plain_text', 'text': 'Timezone'},
        'element': {
            'type': 'static_select',
            'action_id': 'schedule_tz',
            'placeholder': {'type': 'plain_text', 'text': 'Select timezone'},
            'options': tz_options,
            'initial_option': {
                'text': {'type': 'plain_text', 'text': initial_tz},
                'value': initial_tz,
            },
        },
    })

    # Weekday multi-select
    weekday_values = [
        ('Monday', 'mon'), ('Tuesday', 'tue'), ('Wednesday', 'wed'),
        ('Thursday', 'thu'), ('Friday', 'fri'), ('Saturday', 'sat'), ('Sunday', 'sun'),
    ]
    weekday_options = [
        {'text': {'type': 'plain_text', 'text': label}, 'value': val}
        for label, val in weekday_values
    ]
    # Default to mon-fri; for edit, parse existing weekdays
    default_vals = {'mon', 'tue', 'wed', 'thu', 'fri'}
    if existing and existing.get('schedule_weekdays'):
        raw = existing['schedule_weekdays']
        if isinstance(raw, str):
            default_vals = set(raw.split(','))
        else:
            default_vals = set(raw)
    initial_weekday_options = [
        {'text': {'type': 'plain_text', 'text': label}, 'value': val}
        for label, val in weekday_values
        if val in default_vals
    ]
    modal_blocks.append({
        'type': 'input',
        'block_id': 'schedule_weekdays_block',
        'label': {'type': 'plain_text', 'text': 'Weekdays'},
        'element': {
            'type': 'multi_static_select',
            'action_id': 'schedule_weekdays',
            'placeholder': {'type': 'plain_text', 'text': 'Select days'},
            'options': weekday_options,
            'initial_options': initial_weekday_options if initial_weekday_options else None,
        },
    })

    return {
        'type': 'modal',
        'callback_id': CALLBACK_SCHEDULE_CHANNEL,
        'title': {'type': 'plain_text', 'text': 'Channel Schedule'},
        'submit': {'type': 'plain_text', 'text': 'Save'},
        'close': {'type': 'plain_text', 'text': 'Cancel'},
        'private_metadata': json.dumps(private_meta),
        'blocks': modal_blocks,
    }


def build_poll_size_modal(current_size=None, current_smart=None, team_id=None):
    """Build the poll size configuration modal.

    Args:
        current_size: current total poll options, or None
        current_smart: current smart picks count, or None
        team_id: workspace team ID for private_metadata

    Returns:
        Modal view dict
    """
    size_options = [
        {'text': {'type': 'plain_text', 'text': str(n)}, 'value': str(n)}
        for n in [3, 4, 5, 6, 7, 8]
    ]
    initial_size = str(current_size) if current_size is not None else '5'
    size_element = {
        'type': 'static_select',
        'action_id': 'poll_total',
        'options': size_options,
        'initial_option': {
            'text': {'type': 'plain_text', 'text': initial_size},
            'value': initial_size,
        },
    }

    smart_options = [
        {'text': {'type': 'plain_text', 'text': str(n)}, 'value': str(n)}
        for n in [0, 1, 2, 3, 4]
    ]
    initial_smart = str(current_smart) if current_smart is not None else '2'
    smart_element = {
        'type': 'static_select',
        'action_id': 'smart_count',
        'options': smart_options,
        'initial_option': {
            'text': {'type': 'plain_text', 'text': initial_smart},
            'value': initial_smart,
        },
    }

    return {
        'type': 'modal',
        'callback_id': CALLBACK_POLL_SIZE,
        'title': {'type': 'plain_text', 'text': 'Poll Options'},
        'submit': {'type': 'plain_text', 'text': 'Save Options'},
        'close': {'type': 'plain_text', 'text': 'Keep Current Options'},
        'private_metadata': json.dumps({'team_id': team_id}),
        'blocks': [
            {
                'type': 'input',
                'block_id': 'poll_total_block',
                'label': {'type': 'plain_text', 'text': 'Total poll options'},
                'element': size_element,
            },
            {
                'type': 'input',
                'block_id': 'smart_count_block',
                'label': {'type': 'plain_text', 'text': 'Smart picks (Thompson sampling)'},
                'element': smart_element,
            },
            {
                'type': 'context',
                'elements': [{
                    'type': 'mrkdwn',
                    'text': "Smart picks use your team's voting history to suggest restaurants you're likely to enjoy. The rest are random.",
                }],
            },
        ],
    }


def _build_channel_schedules_section(schedules, is_admin):
    """Build the per-channel poll schedules section for App Home (D-14, D-16).

    Args:
        schedules: list of channel_schedule dicts with channel_id,
                   schedule_time, schedule_timezone, schedule_weekdays
        is_admin: whether the viewing user is a workspace admin
    """
    blocks = [
        {'type': 'header', 'text': {'type': 'plain_text', 'text': 'Per-channel poll schedules'}},
    ]

    if not schedules:
        blocks.append({
            'type': 'context',
            'elements': [{'type': 'mrkdwn', 'text': 'No channel schedules yet \u2014 click Schedule a channel to add one.'}],
        })
    else:
        for sched in schedules:
            channel_id = sched.get('channel_id', '')
            sched_time = sched.get('schedule_time')
            if sched_time and hasattr(sched_time, 'hour'):
                time_str = _format_time_12h(sched_time)
            else:
                time_str = str(sched_time) if sched_time else ''
            tz = sched.get('schedule_timezone', '')
            weekdays = sched.get('schedule_weekdays', '')
            if isinstance(weekdays, list):
                weekdays = ','.join(weekdays)
            section = {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'<#{channel_id}> \u2014 {time_str} {tz} \u2014 {weekdays}',
                },
            }
            if is_admin:
                section['accessory'] = {
                    'type': 'button',
                    'text': {'type': 'plain_text', 'text': 'Edit'},
                    'action_id': ACTION_EDIT_CHANNEL_SCHEDULE,
                    'value': channel_id,
                }
            blocks.append(section)

    if is_admin:
        blocks.append({
            'type': 'actions',
            'elements': [{
                'type': 'button',
                'text': {'type': 'plain_text', 'text': 'Schedule a channel'},
                'action_id': ACTION_OPEN_SCHEDULE_CHANNEL_MODAL,
                'style': 'primary',
            }],
        })

    return blocks


def _build_offices_section(locations, is_admin):
    """Build the Offices section for App Home State B (Phase 07.1 Plan 06)."""
    blocks = [
        {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': ':office: *Offices*'},
        },
        {
            'type': 'actions',
            'elements': [{
                'type': 'button',
                'action_id': ACTION_ADD_OFFICE_FROM_HOME,
                'text': {'type': 'plain_text', 'text': 'Add office'},
                'style': 'primary',
            }],
        },
    ]

    if not locations:
        blocks.append({
            'type': 'context',
            'elements': [{
                'type': 'mrkdwn',
                'text': '_No offices yet — add one to get started._',
            }],
        })
        return blocks

    for loc in locations:
        badge = '  :star: *default*' if loc.get('is_default') else ''
        blocks.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f"*{loc['name']}*{badge}\n_{loc['lat_lng']}_",
            },
        })
        if is_admin:
            elements = [{
                'type': 'button',
                'action_id': ACTION_RENAME_OFFICE,
                'text': {'type': 'plain_text', 'text': 'Rename'},
                'value': str(loc['id']),
            }]
            if not loc.get('is_default'):
                elements.append({
                    'type': 'button',
                    'action_id': ACTION_SET_DEFAULT_OFFICE,
                    'text': {'type': 'plain_text', 'text': 'Set default'},
                    'value': str(loc['id']),
                })
            elements.append({
                'type': 'button',
                'action_id': ACTION_DELETE_OFFICE,
                'text': {'type': 'plain_text', 'text': 'Delete'},
                'style': 'danger',
                'value': str(loc['id']),
            })
            blocks.append({'type': 'actions', 'elements': elements})

    return blocks


def build_rename_office_modal(team_id, location_id, current_name):
    """Build the rename-office modal (Phase 07.1 Plan 06)."""
    return {
        'type': 'modal',
        'callback_id': CALLBACK_RENAME_OFFICE,
        'title': {'type': 'plain_text', 'text': 'Rename office'},
        'submit': {'type': 'plain_text', 'text': 'Save'},
        'close': {'type': 'plain_text', 'text': 'Cancel'},
        'private_metadata': json.dumps(
            {'team_id': team_id, 'location_id': location_id},
        ),
        'blocks': [{
            'type': 'input',
            'block_id': 'office_name_block',
            'label': {'type': 'plain_text', 'text': 'Office name'},
            'element': {
                'type': 'plain_text_input',
                'action_id': 'office_name_input',
                'initial_value': current_name or '',
                'max_length': 80,
            },
        }],
    }


def build_delete_office_modal(team_id, location_id, current_name):
    """Build the delete-office confirmation modal (Phase 07.1 Plan 06)."""
    return {
        'type': 'modal',
        'callback_id': CALLBACK_DELETE_OFFICE,
        'title': {'type': 'plain_text', 'text': 'Delete office'},
        'submit': {'type': 'plain_text', 'text': 'Delete'},
        'close': {'type': 'plain_text', 'text': 'Cancel'},
        'private_metadata': json.dumps({
            'team_id': team_id,
            'location_id': location_id,
            'name': current_name,
        }),
        'blocks': [{
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': (
                    f"Delete *{current_name}*? Any channels bound to this office "
                    'will be unbound and will prompt for a new office on the next '
                    '`/lunch`.'
                ),
            },
        }],
    }


