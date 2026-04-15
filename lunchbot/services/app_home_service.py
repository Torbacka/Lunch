"""App Home Block Kit builders for settings panel and configuration modals.

Builds all Slack Block Kit views for the App Home tab per 05-UI-SPEC.md.
Each function returns a dict ready to pass to views.publish or views.open.
"""
import json

# Action IDs for button clicks
ACTION_BEGIN_SETUP = 'app_home_begin_setup'
ACTION_EDIT_CHANNEL = 'app_home_edit_channel'
ACTION_EDIT_SCHEDULE = 'app_home_edit_schedule'
ACTION_EDIT_POLL_SIZE = 'app_home_edit_poll_size'
ACTION_REMOVE_SCHEDULE = 'app_home_remove_schedule'

# Offices section action IDs (Phase 07.1 Plan 06)
ACTION_ADD_OFFICE_FROM_HOME = 'app_home_add_office'
ACTION_RENAME_OFFICE = 'app_home_rename_office'
ACTION_SET_DEFAULT_OFFICE = 'app_home_set_default_office'
ACTION_DELETE_OFFICE = 'app_home_delete_office'

# Callback IDs for modal submissions
CALLBACK_CHANNEL = 'modal_channel'
CALLBACK_SCHEDULE = 'modal_schedule'
CALLBACK_POLL_SIZE = 'modal_poll_size'
CALLBACK_REMOVE_SCHEDULE = 'modal_remove_schedule'
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


def build_home_view(settings, is_admin=True, locations=None):
    """Build the App Home tab view.

    Args:
        settings: dict from get_workspace_settings(), or None for fresh workspace
        is_admin: whether the viewing user is a workspace admin
        locations: list of workspace_location rows (as from list_workspace_locations)
                   or None. Caller is responsible for fetching; this module stays
                   DB-free.

    Returns:
        dict with type 'home' and blocks list
    """
    is_configured = settings is not None and settings.get('poll_channel') is not None
    locations = locations or []

    if is_configured:
        blocks = _build_state_b(settings, is_admin, locations)
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


def _build_state_b(settings, is_admin, locations=None):
    """State B: configured workspace with channel set."""
    locations = locations or []
    blocks = [
        {'type': 'header', 'text': {'type': 'plain_text', 'text': 'LunchBot Settings'}},
        {'type': 'divider'},
    ]

    # Poll Channel row
    channel_id = settings.get('poll_channel', '')
    channel_section = {
        'type': 'section',
        'text': {
            'type': 'mrkdwn',
            'text': f':hash: *Poll Channel*\n<#{channel_id}>',
        },
    }
    if is_admin:
        channel_section['accessory'] = {
            'type': 'button',
            'text': {'type': 'plain_text', 'text': 'Edit'},
            'action_id': ACTION_EDIT_CHANNEL,
        }
    blocks.append(channel_section)
    blocks.append({'type': 'divider'})

    # Schedule row
    schedule_time = settings.get('poll_schedule_time')
    schedule_tz = settings.get('poll_schedule_timezone')
    schedule_days = settings.get('poll_schedule_weekdays')

    has_schedule = schedule_time is not None

    if has_schedule:
        time_str = _format_time_12h(schedule_time)
        days_str = ', '.join(schedule_days) if schedule_days else ''
        schedule_section = {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f':clock3: *Poll Schedule*\n{time_str}, {schedule_tz}\n{days_str}',
            },
        }
        if is_admin:
            schedule_section['accessory'] = {
                'type': 'button',
                'text': {'type': 'plain_text', 'text': 'Edit'},
                'action_id': ACTION_EDIT_SCHEDULE,
            }
        blocks.append(schedule_section)

        if is_admin:
            blocks.append({
                'type': 'actions',
                'elements': [{
                    'type': 'button',
                    'text': {'type': 'plain_text', 'text': 'Remove Schedule'},
                    'action_id': ACTION_REMOVE_SCHEDULE,
                    'style': 'danger',
                }],
            })
    else:
        schedule_section = {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': ':clock3: *Poll Schedule*\nNo schedule configured. Polls are triggered manually with `/lunch`.',
            },
        }
        if is_admin:
            schedule_section['accessory'] = {
                'type': 'button',
                'text': {'type': 'plain_text', 'text': 'Set Schedule'},
                'action_id': ACTION_EDIT_SCHEDULE,
            }
        blocks.append(schedule_section)

    blocks.append({
        'type': 'context',
        'elements': [{'type': 'mrkdwn', 'text': 'Polls post automatically at the scheduled time.'}],
    })
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


def build_channel_modal(current_channel=None, team_id=None):
    """Build the channel selection modal.

    Args:
        current_channel: current poll channel ID, or None
        team_id: workspace team ID for private_metadata

    Returns:
        Modal view dict
    """
    element = {
        'type': 'conversations_select',
        'action_id': 'channel_select',
        'filter': {
            'include': ['public', 'private'],
            'exclude_bot_users': True,
        },
    }
    if current_channel:
        element['initial_conversation'] = current_channel

    return {
        'type': 'modal',
        'callback_id': CALLBACK_CHANNEL,
        'title': {'type': 'plain_text', 'text': 'Poll Channel'},
        'submit': {'type': 'plain_text', 'text': 'Save Channel'},
        'close': {'type': 'plain_text', 'text': 'Keep Current Channel'},
        'private_metadata': json.dumps({'team_id': team_id}),
        'blocks': [
            {
                'type': 'input',
                'block_id': 'channel_select_block',
                'label': {'type': 'plain_text', 'text': 'Channel'},
                'element': element,
            },
        ],
    }


def build_schedule_modal(current_time=None, current_tz=None, current_days=None, team_id=None):
    """Build the schedule configuration modal.

    Args:
        current_time: current schedule time (datetime.time), or None
        current_tz: current timezone string, or None
        current_days: current weekday list, or None
        team_id: workspace team ID for private_metadata

    Returns:
        Modal view dict
    """
    # Time picker
    time_element = {
        'type': 'timepicker',
        'action_id': 'schedule_time',
        'placeholder': {'type': 'plain_text', 'text': 'Select time'},
    }
    if current_time:
        time_element['initial_time'] = f'{current_time.hour:02d}:{current_time.minute:02d}'
    else:
        time_element['initial_time'] = '11:30'

    # Timezone select
    tz_options = [
        {
            'text': {'type': 'plain_text', 'text': tz},
            'value': tz,
        }
        for tz in TIMEZONE_OPTIONS
    ]
    initial_tz = current_tz or 'Europe/Stockholm'
    tz_element = {
        'type': 'static_select',
        'action_id': 'schedule_tz',
        'placeholder': {'type': 'plain_text', 'text': 'Select timezone'},
        'options': tz_options,
        'initial_option': {
            'text': {'type': 'plain_text', 'text': initial_tz},
            'value': initial_tz,
        },
    }

    # Weekday checkboxes
    day_options = [
        {
            'text': {'type': 'plain_text', 'text': day},
            'value': day,
        }
        for day in WEEKDAYS
    ]
    initial_days = current_days or ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    initial_day_options = [
        {
            'text': {'type': 'plain_text', 'text': day},
            'value': day,
        }
        for day in initial_days
    ]
    days_element = {
        'type': 'checkboxes',
        'action_id': 'schedule_days',
        'options': day_options,
        'initial_options': initial_day_options,
    }

    return {
        'type': 'modal',
        'callback_id': CALLBACK_SCHEDULE,
        'title': {'type': 'plain_text', 'text': 'Poll Schedule'},
        'submit': {'type': 'plain_text', 'text': 'Save Schedule'},
        'close': {'type': 'plain_text', 'text': 'Keep Current Schedule'},
        'private_metadata': json.dumps({'team_id': team_id}),
        'blocks': [
            {
                'type': 'input',
                'block_id': 'schedule_time_block',
                'label': {'type': 'plain_text', 'text': 'Time'},
                'element': time_element,
            },
            {
                'type': 'input',
                'block_id': 'schedule_tz_block',
                'label': {'type': 'plain_text', 'text': 'Timezone'},
                'element': tz_element,
            },
            {
                'type': 'input',
                'block_id': 'schedule_days_block',
                'label': {'type': 'plain_text', 'text': 'Days'},
                'element': days_element,
            },
        ],
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


def build_remove_schedule_modal(team_id=None):
    """Build the remove schedule confirmation modal.

    Args:
        team_id: workspace team ID for private_metadata

    Returns:
        Modal view dict
    """
    return {
        'type': 'modal',
        'callback_id': CALLBACK_REMOVE_SCHEDULE,
        'title': {'type': 'plain_text', 'text': 'Remove Schedule'},
        'submit': {'type': 'plain_text', 'text': 'Remove Schedule'},
        'close': {'type': 'plain_text', 'text': 'Keep Schedule'},
        'private_metadata': json.dumps({'team_id': team_id}),
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': "Are you sure you want to remove the automatic poll schedule? Polls will only be triggered manually with `/lunch`.",
                },
            },
        ],
    }
