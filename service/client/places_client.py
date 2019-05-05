import os

import requests

password = os.environ['PLACES_PASSWORD']
session = requests.Session()


def find_suggestion(search_string):
    params = {
        'location': '59.3419128,18.0644956',
        'radius': 600,
        'keyword': search_string,
        'type': 'restaurant',
        'key': password
    }
    return session.get("https://maps.googleapis.com/maps/api/place/nearbysearch/json", params=params).json()


def get_details(place_id):
    params = {
        'placeid': place_id,
        'key': password
    }
    return session.get("https://maps.googleapis.com/maps/api/place/details/json", params=params).json()


if __name__ == '__main__':
    find_suggestion("Mae")
