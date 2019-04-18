import html

import requests

from service import mongo_client, slack_client


def vote(payload):
    choice = int(payload['actions'][0]['value']) - 1
    user_id = payload['user']['id']
    votes = mongo_client.update_vote(choice, user_id)

    original_message = payload['original_message']
    json_data = update_message(original_message, votes)
    json_data['ts'] = payload['message_ts']
    json_data['as_user'] = True
    json_data['channel'] = payload['channel']['id']
    slack_client.update_message(json_data)


def update_message(json_data, votes):
    for index, suggestion in enumerate(votes['suggestions'], start=0):
        attachment = json_data['attachments'][0]
        user_ids = list("<@{}>".format(user_id) for user_id in suggestion['votes'])
        user_string = ' '.join(user_ids)
        stripped_value_string = attachment['fields'][index]['value'].split("\n")[0]
        attachment['fields'][index]['title'] = html.unescape(attachment['fields'][index]['title'])
        attachment['fields'][index]['value'] = "{}\n{}".format(stripped_value_string, user_string)
    return json_data
