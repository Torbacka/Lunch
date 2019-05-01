import json
from datetime import date

from service.client import mongo_client, slack_client


def push_suggestions():
    votes = mongo_client.get_votes(date.today())
    with open('resources/lunch_message_template.json') as json_file:
        lunch_message = json.load(json_file)
        blocks = lunch_message['blocks']
        for index, vote in enumerate(votes['suggestions'], start=1):
            blocks.append(add_restaurant_text(index, vote['name'], vote['rating']))
            blocks.append(add_vote_section(vote['url']))
        slack_client.post_message(lunch_message)


def add_restaurant_text(index, name, rating):
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"{index}. {name} *{rating}*:star:"
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "vote",
                "emoji": True
            },
            "value": f"{index}"
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
        "type": "divider"
    }, {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"For more info: {url}"
            }
        ]
    }]


def suggest(place_id):
    mongo_client.update_suggestions(place_id)
