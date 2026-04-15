"""Builders for the 'Add a new office' Slack modal.

Used by both the /lunch always-prompt flow (Phase 07.1 plan 05) and the App
Home Offices section (plan 06). The modal has a single Places-backed
external_select; submission creates a workspace_locations row and (for the
/lunch flow) binds the current channel to it.
"""
import json

CALLBACK_ADD_OFFICE = 'modal_add_office'
OFFICE_SEARCH_SELECT = 'office_search_select'
OFFICE_SEARCH_BLOCK = 'office_search_block'


def build_add_office_modal(team_id, channel_id=None):
    """Build the Slack modal for adding a new office.

    channel_id is optional: when present (the /lunch flow), submission also
    binds that channel. When absent (the App Home flow), submission only
    creates the office.
    """
    metadata = {'team_id': team_id}
    if channel_id:
        metadata['channel_id'] = channel_id

    return {
        'type': 'modal',
        'callback_id': CALLBACK_ADD_OFFICE,
        'title': {'type': 'plain_text', 'text': 'Add an office'},
        'submit': {'type': 'plain_text', 'text': 'Add office'},
        'close': {'type': 'plain_text', 'text': 'Cancel'},
        'private_metadata': json.dumps(metadata),
        'blocks': [
            {
                'type': 'input',
                'block_id': OFFICE_SEARCH_BLOCK,
                'label': {'type': 'plain_text', 'text': 'Search for an address'},
                'element': {
                    'type': 'external_select',
                    'action_id': OFFICE_SEARCH_SELECT,
                    'min_query_length': 3,
                    'placeholder': {'type': 'plain_text', 'text': 'e.g. Spotify HQ, Stockholm'},
                },
            },
            {
                'type': 'context',
                'elements': [{
                    'type': 'mrkdwn',
                    'text': "We'll use this address to find nearby restaurants.",
                }],
            },
        ],
    }
