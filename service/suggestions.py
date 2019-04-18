import json
from datetime import date

from service import mongo_client, slack_client


def push_suggestions():
    votes = mongo_client.get_votes(date.today())
    with open('resources/lunch_message_template.json') as json_file:
        lunch_message = json.load(json_file)
        attachments = lunch_message['attachments']
        for index, vote in enumerate(votes['suggestions'], start=1):
            attachments[0]['fields'].append({
                'short': False,
                'title': " {}. {} ({})".format(index, vote['name'], vote['rating']),
                'value': "<{}>".format(vote['url'])
            })
            attachments[1]['actions'].append({
                "id": index,
                "name": "vote",
                "style": "",
                "text": index,
                "type": "button",
                "value": index
            })
        slack_client.post_message(lunch_message)




def suggest(place_id):
    mongo_client.update_suggestions(place_id)
