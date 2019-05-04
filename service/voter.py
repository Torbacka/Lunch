import json
import operator
from functools import reduce

from service.client import mongo_client, slack_client


def vote(payload):
    choice = int(payload['actions'][0]['value']) - 1
    user_id = payload['user']['id']
    votes = mongo_client.update_vote(choice, user_id)

    blocks = payload['message']['blocks']
    return_message = dict()
    return_message['blocks'] = update_message(blocks, votes)
    return_message['ts'] = payload['message']['ts']
    return_message['as_user'] = True
    return_message['channel'] = payload['channel']['id']
    print(json.dumps(blocks))
    slack_client.update_message(return_message)


def update_message(blocks, votes):
    for index, suggestion in enumerate(votes['suggestions'], start=0):
        votes = add_user_votes(suggestion)
        number_of_votes = len(suggestion['votes'])
        votes.append({
            "type": "plain_text",
            "emoji": True,
            "text": f"{number_of_votes if number_of_votes > 0 else 'No'} {'votes' if number_of_votes != 1 else 'vote'}"
        })
        blocks[index * 4 + 3]['elements'] = votes

    sorted_blocks = sort_message(blocks)
    index = 1
    for block in sorted_blocks:
        if 'accessory' in block:
            block['accessory']['value'] = f"{index}"
            index += 1
    return sorted_blocks


def sort_message(blocks):
    first_part = blocks[:2]
    suggestions = blocks[2:]
    grouped_suggestions = group_suggestions(suggestions)
    suggestions = sorted(grouped_suggestions, key=lambda k: len(k[1]['elements']), reverse=True)
    first_part.extend(reduce(operator.concat, suggestions))
    return first_part


def group_suggestions(suggestions):
    grouped_suggestions = list()
    i = 0
    while i < len(suggestions):
        grouped_suggestion = list()
        for n in range(4):
            grouped_suggestion.append(suggestions[i + n])
        i += 4
        grouped_suggestions.append(grouped_suggestion)
    return grouped_suggestions


def add_user_votes(suggestion):
    votes = []
    for user_id in suggestion['votes']:
        profile = slack_client.get_profile_pic(user_id)
        votes.append({
            'type': 'image',
            'image_url': profile['image_24'],
            'alt_text': f'{profile["display_name"]}'
        })
    return votes
