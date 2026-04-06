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
ACTION_EDIT_LOCATION = 'app_home_edit_location'
ACTION_REMOVE_SCHEDULE = 'app_home_remove_schedule'

# Callback IDs for modal submissions
CALLBACK_CHANNEL = 'modal_channel'
CALLBACK_SCHEDULE = 'modal_schedule'
CALLBACK_POLL_SIZE = 'modal_poll_size'
CALLBACK_LOCATION = 'modal_location'
CALLBACK_REMOVE_SCHEDULE = 'modal_remove_schedule'

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


def build_home_view(settings, is_admin=True):
    """Build the App Home tab view.

    Args:
        settings: dict from get_workspace_settings(), or None for fresh workspace
        is_admin: whether the viewing user is a workspace admin

    Returns:
        dict with type 'home' and blocks list
    """
    is_configured = settings is not None and settings.get('poll_channel') is not None

    if is_configured:
        blocks = _build_state_b(settings, is_admin)
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


def _build_state_b(settings, is_admin):
    """State B: configured workspace with channel set."""
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

    # Location row
    location = settings.get('location') or 'Not set'
    location_section = {
        'type': 'section',
        'text': {
            'type': 'mrkdwn',
            'text': f':round_pushpin: *Location*\n{location}',
        },
    }
    if is_admin:
        location_section['accessory'] = {
            'type': 'button',
            'text': {'type': 'plain_text', 'text': 'Edit'},
            'action_id': ACTION_EDIT_LOCATION,
        }
    blocks.append(location_section)
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


def build_location_modal(current_location=None, team_id=None):
    """Build the location configuration modal.

    Args:
        current_location: current location string, or None
        team_id: workspace team ID for private_metadata

    Returns:
        Modal view dict
    """
    location_element = {
        'type': 'plain_text_input',
        'action_id': 'location_input',
        'placeholder': {'type': 'plain_text', 'text': 'e.g. Stockholm, Sweden'},
    }
    if current_location:
        location_element['initial_value'] = current_location

    return {
        'type': 'modal',
        'callback_id': CALLBACK_LOCATION,
        'title': {'type': 'plain_text', 'text': 'Search Location'},
        'submit': {'type': 'plain_text', 'text': 'Save Location'},
        'close': {'type': 'plain_text', 'text': 'Keep Current Location'},
        'private_metadata': json.dumps({'team_id': team_id}),
        'blocks': [
            {
                'type': 'input',
                'block_id': 'location_input_block',
                'label': {'type': 'plain_text', 'text': 'Location'},
                'element': location_element,
            },
            {
                'type': 'context',
                'elements': [{
                    'type': 'mrkdwn',
                    'text': 'This location is used to search for nearby restaurants via Google Places.',
                }],
            },
        ],
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
