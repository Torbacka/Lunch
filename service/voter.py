from service.client import mongo_client, slack_client


def vote(payload):
    choice = int(payload['actions'][0]['value'])
    user_id = payload['user']['id']
    votes = mongo_client.update_vote(choice, user_id)

    blocks = payload['message']['blocks']
    json_data = update_message(blocks, votes)
    json_data['ts'] = payload['message_ts']
    json_data['as_user'] = True
    json_data['channel'] = payload['channel']['id']
    slack_client.update_message(json_data)


def update_message(blocks, votes):
    for index, suggestion in enumerate(votes['suggestions'], start=1):
        votes = add_user_votes(suggestion)
        votes.append({
            "type": "plain_text",
            "emoji": True,
            "text": f"{len(suggestion['votes'])} votes"
        })
        blocks[index * 4]['elements'] = votes
    return blocks


def add_user_votes(suggestion):
    votes = []
    for user_id in suggestion['votes']:
        profile = slack_client.get_profile_pic(user_id)
        votes.append({
            'type': 'image',
            'image_url': profile['image_24'],
            'alt_text': f'{profile["display_name"]}'
        })
    return votes
