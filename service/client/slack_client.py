import json
import os

import requests

slack_url = "https://slack.com/api/"
slack_token = os.environ['SLACK_TOKEN']
bot_token = os.environ['BOT_TOKEN']
session = requests.Session()


def get_headers(token):
    return {
        'Content-Type': 'application/json;charset=utf-8',
        'Authorization': f'Bearer {token}'
    }


def get_from_headers(token):
    return {
        'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
        'Authorization': f'Bearer {token}'
    }


def get_profile_pic(user_id):
    response = session.post("https://slack.com/api/users.profile.get", headers=get_from_headers(slack_token), data={'user': user_id})
    print("Status code: {}   response: {} ".format(response.status_code, response.json()))
    return response.json()['profile']


def post_message(data):
    """
    Method to post data to slack
    :param data: The message that should be send to slack
    :return: Returning the unique id of the message.
    """
    response = session.post("https://slack.com/api/chat.postMessage", headers=get_headers(bot_token), json=data)
    print("Status code: {}   response: {} ".format(response.status_code, response.json()))
    return response.json()['ts']


def update_message(data):
    response = session.post("https://slack.com/api/chat.update", headers=get_headers(bot_token), json=data)
    print("Slack response status code: {}   response: {} ".format(response.status_code, response.json()))
