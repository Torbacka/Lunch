import json
from datetime import date

from service.client import mongo_client, slack_client


def push_suggestions():
    votes = mongo_client.get_votes(date.today())
    with open('resources/lunch_message_template.json') as json_file:
        lunch_message = json.load(json_file)
        blocks = lunch_message['blocks']
        for key, vote in votes['suggestions'].items():
            print(vote)
            blocks.append(add_restaurant_text(vote['place_id'], vote.get('emoji', None), vote['name'], vote['rating']))
            blocks.extend(add_vote_section(vote['url']))
        print(json.dumps(lunch_message))
        slack_client.post_message(lunch_message)


def add_restaurant_text(place_id, emoji, name, rating):
    if emoji is None:
        emoji = 'knife_fork_plate'
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f":{emoji}: *{name}* {rating}:star:"
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "vote",
                "emoji": True
            },
            "value": f"{place_id}"
        }
    }


def add_vote_section(url):
    return [{
        "type": "context",
        "elements": [
            {
                "type": "plain_text",
                "emoji": True,
                "text": "No votes"
            }
        ]
    }, {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"For more info: {url}"
            }
        ]
    }, {
        "type": "divider"
    }]


def suggest(place_id):
    mongo_client.update_suggestions(place_id)
