import os

import requests

slack_url = "https://slack.com/api/"
slack_token = os.environ['SLACK_TOKEN']
headers = {
    'Content-Type': 'application/json;charset=utf-8',
    'Authorization': f'Bearer {slack_token}'
}


def post_message(data):
    response = requests.post("https://slack.com/api/chat.postMessage", headers=headers, json=data)
    print("Status code: {}   response: {} ".format(response.status_code, response.json()))


def update_message(data):
    response = requests.post("https://slack.com/api/chat.update", headers=headers, json=data)
    print("Status code: {}   response: {} ".format(response.status_code, response.json()))
