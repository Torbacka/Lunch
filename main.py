import json

from flask import request, Flask, jsonify

from service import voter, suggestions, places_client, mongo_client, slack_client

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
    if payload['actions'][0]['name'] == 'suggest':
        suggestions.suggest(payload['actions'][0]['selected_options'][0]['value'])
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


def suggestion_message():
    with open('resources/suggestion_template.json') as json_file:
        message = json.load(json_file)
        slack_client.post_message(message)


def find_suggestions(request):
    payload = json.loads(request.form["payload"])
    restaurants = places_client.find_suggestion(payload['value'])
    mongo_client.save_restaurants_info(restaurants)
    options = list({'text': restaurant['name'], 'value': restaurant['place_id']} for restaurant in restaurants['results'])
    return {'options': options}


@app.route('/find_suggestions', methods=['POST'])
def push_slack():
    ret = find_suggestions(request)
    return jsonify(ret)


@app.route('/lunch_message')
def send_lunch_message():
    lunch_message(request)
    return ''


@app.route('/action', methods=['POST'])
def local_action():
    action(request)
    return ''


if __name__ == '__main__':
    app.run('127.0.0.1', port=8087, debug=True)
