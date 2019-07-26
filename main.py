import json

from flask import request, Flask, jsonify

from service import voter, suggestions
from service.client import places_client, mongo_client, slack_client
from service.emoji import search_and_update_emoji

app = Flask(__name__)


def action(request):
    """Seeder cloud function.
    Args:
        request (flask.Request): Contains an slack action that will be used to update the lunch vote.
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>.
    """
    payload = json.loads(request.form["payload"])
    print(json.dumps(payload))
    if payload['actions'][0]['type'] == 'external_select':
        suggestions.suggest(payload['actions'][0]['selected_option']['value'])
    else:
        voter.vote(payload)
    return ''


def lunch_message(request):
    """
    Lunch message cloud functions, used to construct and push lunch message to slack.
    :param request: GET request is just used to trigger the function
    :return: Returns http status codes depending on the error.
    """
    suggestions.push_suggestions()


def suggestion_message(request):
    with open('resources/suggestion_template.json') as json_file:
        message = json.load(json_file)
        slack_client.post_message(message)
    return ''


def find_suggestions(request):
    payload = json.loads(request.form["payload"])
    print(json.dumps(payload))
    restaurants = places_client.find_suggestion(payload['value'])
    mongo_client.save_restaurants_info(restaurants)
    options = list(
        {
            'text': {
                "type": "plain_text",
                "text": f"{restaurant['name']} {restaurant['opening_hours']['open_now'] if 'open' else 'close'} {restaurant['rating']}"
            },
            'value': restaurant['place_id']
        } for restaurant in restaurants['results'])
    return jsonify({'options': options})


def emoji():
    search_and_update_emoji()
    return ''


@app.route('/find_suggestions', methods=['POST'])
def push_slack():
    ret = find_suggestions(request)
    print(ret)
    return ret


@app.route('/lunch_message')
def send_lunch_message():
    lunch_message(request)
    return ''


@app.route('/suggestion_message')
def send_suggestion_message():
    suggestion_message(request)
    return ''


@app.route('/action', methods=['POST'])
def local_action():
    action(request)
    return ''


@app.route('/emoji', methods=['GET'])
def local_emoji():
    emoji()
    return ''


if __name__ == '__main__':
    app.run('127.0.0.1', port=8087, debug=True)
