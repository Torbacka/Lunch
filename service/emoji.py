import json

from service.client.mongo_client import add_emoji
from service.client.places_client import find_suggestion


def search_and_update_emoji():
    with open('resources/food_emoji.json') as json_file:
        emojis = json.load(json_file)
        for emoji in emojis:
            suggestions = search_suggestions(emoji)
            print(suggestions)
            update_database(suggestions, emoji['emoji'])


def search_suggestions(emoji):
    search_query = emoji['search_query']
    result = dict()
    for search in search_query:
        print(f"Searching for {search} in nearby searches")
        suggestions = find_suggestion(search)
        result.update(suggestions.copy())
    return result


def update_database(suggestions, emoji):
    place_ids = []
    for suggestion in suggestions['results']:
        print("Updating suggestion")
        place_ids.append(suggestion['place_id'])
    print(place_ids)
    add_emoji(place_ids, emoji)
