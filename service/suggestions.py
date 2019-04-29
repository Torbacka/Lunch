import json
from datetime import date

from service import mongo_client, slack_client


def push_suggestions():
    votes = mongo_client.get_votes(date.today())
    with open('resources/lunch_message_template.json') as json_file:
        lunch_message = json.load(json_file)
        attachments = lunch_message['attachments']
        vote_index = 1
        for index, vote in enumerate(votes['suggestions'], start=1):
            attachments[0]['fields'].append({
                'short': False,
                'title': " {}. {} ({})".format(index, vote['name'], vote['rating']),
                'value': "<{}>".format(vote['url'])
            })
            add_actions(attachments, index, vote_index)
        slack_client.post_message(lunch_message)


def add_actions(attachments, index, vote_index):
    attachments[vote_index]['actions'].append({
        "id": index,
        "name": "vote",
        "style": "",
        "text": index,
        "type": "button",
        "value": index
    })
    if index % 5 == 0:
        vote_index += 1
        attachments.append({
            "actions": [
            ],
            "callback_id": "vote",
            "color": "3AA3E3",
            "fallback": "Something wrong happend",
            "id": 2,
            "text": "Choose a resturant"
        })


def suggest(place_id):
    mongo_client.update_suggestions(place_id)
