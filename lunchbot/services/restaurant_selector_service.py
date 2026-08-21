"""Slack Block Kit helpers for adding Google and custom restaurants."""
import base64
import json


ACTION_ADD_RESTAURANT = 'poll_add_restaurant'
CALLBACK_ADD_CUSTOM_RESTAURANT = 'modal_add_custom_restaurant'
CUSTOM_OPTION_PREFIX = 'custom_text:'
CUSTOM_NAME_ACTION = 'custom_restaurant_name'
CUSTOM_NAME_BLOCK = 'custom_restaurant_name_block'
CUSTOM_ADDRESS_ACTION = 'custom_restaurant_address'
CUSTOM_URL_ACTION = 'custom_restaurant_url'
CUSTOM_URL_BLOCK = 'custom_restaurant_url_block'
CUSTOM_CUISINE_ACTION = 'custom_restaurant_cuisine'


def encode_custom_option(query):
    """Encode free text into a Slack option value without delimiter ambiguity."""
    clean = ' '.join((query or '').split())[:80]
    encoded = base64.urlsafe_b64encode(clean.encode('utf-8')).decode('ascii').rstrip('=')
    while len(encoded) > 130 and clean:
        clean = clean[:-1]
        encoded = base64.urlsafe_b64encode(clean.encode('utf-8')).decode('ascii').rstrip('=')
    return f'{CUSTOM_OPTION_PREFIX}{encoded}'


def decode_custom_option(value):
    """Decode a custom option value, returning None for Google Place IDs."""
    if not (value or '').startswith(CUSTOM_OPTION_PREFIX):
        return None
    encoded = value[len(CUSTOM_OPTION_PREFIX):]
    try:
        padding = '=' * (-len(encoded) % 4)
        return base64.urlsafe_b64decode(encoded + padding).decode('utf-8')
    except (ValueError, UnicodeDecodeError):
        return ''


def build_custom_restaurant_modal(query, team_id, channel_id, message_ts):
    """Build a confirmation modal for an office-owned free-text restaurant."""
    metadata = json.dumps({
        'team_id': team_id,
        'channel_id': channel_id,
        'message_ts': message_ts,
    })
    return {
        'type': 'modal',
        'callback_id': CALLBACK_ADD_CUSTOM_RESTAURANT,
        'private_metadata': metadata,
        'title': {'type': 'plain_text', 'text': 'Add restaurant'},
        'submit': {'type': 'plain_text', 'text': 'Add'},
        'close': {'type': 'plain_text', 'text': 'Cancel'},
        'blocks': [
            {
                'type': 'input',
                'block_id': CUSTOM_NAME_BLOCK,
                'label': {'type': 'plain_text', 'text': 'Restaurant name'},
                'element': {
                    'type': 'plain_text_input',
                    'action_id': CUSTOM_NAME_ACTION,
                    'initial_value': ' '.join((query or '').split())[:80],
                    'max_length': 80,
                },
            },
            {
                'type': 'input',
                'optional': True,
                'label': {'type': 'plain_text', 'text': 'Address or description'},
                'element': {
                    'type': 'plain_text_input',
                    'action_id': CUSTOM_ADDRESS_ACTION,
                    'max_length': 120,
                },
            },
            {
                'type': 'input',
                'optional': True,
                'block_id': CUSTOM_URL_BLOCK,
                'label': {'type': 'plain_text', 'text': 'Website or map URL'},
                'element': {
                    'type': 'url_text_input',
                    'action_id': CUSTOM_URL_ACTION,
                },
            },
            {
                'type': 'input',
                'optional': True,
                'label': {'type': 'plain_text', 'text': 'Cuisine'},
                'element': {
                    'type': 'plain_text_input',
                    'action_id': CUSTOM_CUISINE_ACTION,
                    'max_length': 40,
                },
            },
        ],
    }
