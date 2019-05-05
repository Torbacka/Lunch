import os

import requests

from main import session

slack_url = "https://slack.com/api/"
slack_token = os.environ['SLACK_TOKEN']
bot_token = os.environ['BOT_TOKEN']


def get_headers(token):
    return {
        'Content-Type': 'application/json;charset=utf-8',
        'Authorization': f'Bearer {token}'
    }


def get_profile_pic(user_id):
    response = session.post("https://slack.com/api/users.profile.get", headers=get_headers(slack_token), json={'user': user_id})
    print("Status code: {}   response: {} ".format(response.status_code, response.json()))
    return response.json()['profile']


def post_message(data):
    response = session.post("https://slack.com/api/chat.postMessage", headers=get_headers(bot_token), json=data)
    print("Status code: {}   response: {} ".format(response.status_code, response.json()))


def update_message(data):
    response = session.post("https://slack.com/api/chat.update", headers=get_headers(bot_token), json=data)
    print("Status code: {}   response: {} ".format(response.status_code, response.json()))
