import os
from datetime import date

import pymongo as pymongo
from pymongo import ReturnDocument

from service.client import places_client

password = os.environ['MONGO_PASSWORD']


def get_votes(date_input):
    client = pymongo.MongoClient(f"mongodb://root:{password}@hack-for-sweden-shard-00-00-7vayj.mongodb.net:27017,hack-for-sweden-shard-00-01-7vayj.mongodb.net:27017,"
                                 "hack-for-sweden-shard-00-02-7vayj.mongodb.net:27017/test?ssl=true&replicaSet=hack-for-sweden-shard-0&authSource=admin&retryWrites=true")
    collection = client['lunch']['votes']
    return collection.find_one({'date': date_input.isoformat()})


def get_all_votes():
    client = pymongo.MongoClient(f"mongodb://root:{password}@hack-for-sweden-shard-00-00-7vayj.mongodb.net:27017,hack-for-sweden-shard-00-01-7vayj.mongodb.net:27017,"
                                 "hack-for-sweden-shard-00-02-7vayj.mongodb.net:27017/test?ssl=true&replicaSet=hack-for-sweden-shard-0&authSource=admin&retryWrites=true")
    collection = client['lunch']['votes']
    return collection.find()


def update_vote(place_id, user_id):
    """
    Update the user_id choice, if the user_id already exist in the choice it will be removed.
    :param place_id: What restaurant the user picked
    :param user_id: slack user_id
    """
    client = pymongo.MongoClient(f"mongodb://root:{password}@hack-for-sweden-shard-00-00-7vayj.mongodb.net:27017,hack-for-sweden-shard-00-01-7vayj.mongodb.net:27017,"
                                 "hack-for-sweden-shard-00-02-7vayj.mongodb.net:27017/test?ssl=true&replicaSet=hack-for-sweden-shard-0&authSource=admin&retryWrites=true")
    collection = client['lunch']['votes']
    vote = collection.find_one({'date': date.today().isoformat()})
    # Remove vote
    if user_id in vote['suggestions'][f'{place_id}']['votes']:
        return collection.find_one_and_update(
            filter={'date': date.today().isoformat()},
            update={
                "$pull": {f"suggestions.{place_id}.votes": user_id}
            },
            return_document=ReturnDocument.AFTER
        )
    # Add vote
    else:
        return collection.find_one_and_update(
            filter={'date': date.today().isoformat()},
            update={
                "$addToSet": {f"suggestions.{place_id}.votes": user_id}
            },
            return_document=ReturnDocument.AFTER
        )


def update_suggestions(place_id):
    client = pymongo.MongoClient(f"mongodb://root:{password}@hack-for-sweden-shard-00-00-7vayj.mongodb.net:27017,hack-for-sweden-shard-00-01-7vayj.mongodb.net:27017,"
                                 "hack-for-sweden-shard-00-02-7vayj.mongodb.net:27017/test?ssl=true&replicaSet=hack-for-sweden-shard-0&authSource=admin&retryWrites=true")
    votes_collection = client['lunch']['votes']
    restaurant_collection = client['lunch']['restaurants']
    restaurant = restaurant_collection.find_one({"place_id": place_id})
    if 'url' not in restaurant:
        restaurant = add_restaurant_url(place_id, restaurant, restaurant_collection)
    print(restaurant)
    suggestion = {
        'price_level': restaurant.get("price_level", ''),
        'rating': restaurant.get('rating', ''),
        'name': restaurant['name'],
        'place_id': restaurant['place_id'],
        'url': restaurant['url'],
        'website': restaurant.get('website', ''),
        'emoji': restaurant.get('emoji', None),
        'votes': list(),
    }
    print(suggestion)
    votes_collection.find_one_and_update(
        filter={'date': date.today().isoformat()},
        update={
            "$set": {'date': date.today().isoformat(), f'suggestions.{restaurant["place_id"]}': suggestion}
        },
        upsert=True
    )


def add_emoji(place_ids, emoji_string):
    client = pymongo.MongoClient(f"mongodb://root:{password}@hack-for-sweden-shard-00-00-7vayj.mongodb.net:27017,hack-for-sweden-shard-00-01-7vayj.mongodb.net:27017,"
                                 "hack-for-sweden-shard-00-02-7vayj.mongodb.net:27017/test?ssl=true&replicaSet=hack-for-sweden-shard-0&authSource=admin&retryWrites=true")
    restaurant_collection = client['lunch']['restaurants']
    restaurant = restaurant_collection.update_many(
        filter={'place_id': {"$in": place_ids}},
        update={
            "$set": {
                'emoji': emoji_string,
            }
        }
    )
    print(restaurant)
    return restaurant


def add_restaurant_url(place_id, restaurant, restaurant_collection):
    restaurant_details = places_client.get_details(restaurant['place_id'])
    restaurant = restaurant_collection.find_one_and_update(
        filter={'place_id': place_id},
        update={
            "$set": {
                'url': restaurant_details['result']['url'],
                'website': restaurant_details['result']['website']
            }
        },
        return_document=ReturnDocument.AFTER
    )
    return restaurant


def save_restaurants_info(restaurants):
    client = pymongo.MongoClient(f"mongodb://root:{password}@hack-for-sweden-shard-00-00-7vayj.mongodb.net:27017,hack-for-sweden-shard-00-01-7vayj.mongodb.net:27017,"
                                 "hack-for-sweden-shard-00-02-7vayj.mongodb.net:27017/test?ssl=true&replicaSet=hack-for-sweden-shard-0&authSource=admin&retryWrites=true")
    collection = client['lunch']['restaurants']
    found_place_ids = find_existing_place_id(collection, restaurants)
    for restaurant in restaurants['results']:
        if restaurant['place_id'] in found_place_ids:
            collection.update_one({'place_id': restaurant['place_id']}
                                  , {'$set': {
                    "geometry": restaurant['geometry'],
                    "icon": restaurant['icon'],
                    "id": restaurant['id'],
                    "name": restaurant['name'],
                    "opening_hours": restaurant.get('opening_hours'),
                    "photos": restaurant['photos'],
                    "place_id": restaurant['place_id'],
                    "plus_code": restaurant['plus_code'],
                    "rating": restaurant['rating'],
                    "reference": restaurant['reference'],
                    "types": restaurant['types'],
                    "user_ratings_total": restaurant['user_ratings_total'],
                    "vicinity": restaurant['vicinity']
                }})
        else:
            collection.insert_one(restaurant)


def find_existing_place_id(collection, restaurants):
    place_ids = [dictionary['place_id'] for dictionary in restaurants['results']]
    found_place_ids = []
    print(place_ids)
    for result in collection.find({'place_id': {'$in': place_ids}}):
        found_place_ids.append(result['place_id'])
    return found_place_ids


if __name__ == '__main__':
    save_restaurants_info(None)
