import os
from datetime import date

import pymongo as pymongo
from pymongo import ReturnDocument

from service import places_client

password = os.environ['MONGO_PASSWORD']


def get_votes(date_input):
    client = pymongo.MongoClient("mongodb://root:{}@hack-for-sweden-shard-00-00-7vayj.mongodb.net:27017,hack-for-sweden-shard-00-01-7vayj.mongodb.net:27017,"
                                 "hack-for-sweden-shard-00-02-7vayj.mongodb.net:27017/test?ssl=true&replicaSet=hack-for-sweden-shard-0&authSource=admin&retryWrites=true"
                                 .format(password))
    collection = client['lunch']['votes']
    return collection.find_one({'date': date_input.isoformat()})


def update_vote(choice, user_id):
    """
    Update the user_id choice, if the user_id already exist in the choice it will be removed.
    :param choice: What choice the user made
    :param user_id: slack user_id
    """
    client = pymongo.MongoClient("mongodb://root:{}@hack-for-sweden-shard-00-00-7vayj.mongodb.net:27017,hack-for-sweden-shard-00-01-7vayj.mongodb.net:27017,"
                                 "hack-for-sweden-shard-00-02-7vayj.mongodb.net:27017/test?ssl=true&replicaSet=hack-for-sweden-shard-0&authSource=admin&retryWrites=true"
                                 .format(password))
    collection = client['lunch']['votes']
    vote = collection.find_one({'date': date.today().isoformat()})
    if user_id in vote['suggestions'][choice]['votes']:
        return collection.find_one_and_update(
            filter={'date': date.today().isoformat()},
            update={
                "$pull": {"suggestions.{}.votes".format(choice): user_id}
            },
            return_document=ReturnDocument.AFTER
        )
    else:
        return collection.find_one_and_update(
            filter={'date': date.today().isoformat()},
            update={
                "$addToSet": {"suggestions.{}.votes".format(choice): user_id}
            },
            return_document=ReturnDocument.AFTER
        )


def update_suggestions(place_id):
    client = pymongo.MongoClient("mongodb://root:{}@hack-for-sweden-shard-00-00-7vayj.mongodb.net:27017,hack-for-sweden-shard-00-01-7vayj.mongodb.net:27017,"
                                 "hack-for-sweden-shard-00-02-7vayj.mongodb.net:27017/test?ssl=true&replicaSet=hack-for-sweden-shard-0&authSource=admin&retryWrites=true"
                                 .format(password))
    votes_collection = client['lunch']['votes']
    restaurant_collection = client['lunch']['restaurants']
    restaurant = restaurant_collection.find_one({"place_id": place_id})
    if 'url' not in restaurant:
        restaurant = add_restaurant_url(place_id, restaurant, restaurant_collection)

    suggestion = {
        'price_level': restaurant.get("price_level", ''),
        'rating': restaurant.get('rating', ''),
        'name': restaurant['name'],
        'place_id': restaurant['place_id'],
        'url': restaurant['url'],
        'website': restaurant.get('website', ''),
        'votes': list(),
    }
    votes_collection.find_one_and_update(
        filter={'date': date.today().isoformat()},
        update={
            "$set": {'date': date.today().isoformat()},
            "$addToSet": {"suggestions": suggestion},
        },
        upsert=True
    )


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
    client = pymongo.MongoClient("mongodb://root:{}@hack-for-sweden-shard-00-00-7vayj.mongodb.net:27017,hack-for-sweden-shard-00-01-7vayj.mongodb.net:27017,"
                                 "hack-for-sweden-shard-00-02-7vayj.mongodb.net:27017/test?ssl=true&replicaSet=hack-for-sweden-shard-0&authSource=admin&retryWrites=true"
                                 .format(password))
    collection = client['lunch']['restaurants']
    for restaurant in restaurants['results']:
        collection.update({'place_id': restaurant['place_id']}
                          , restaurant
                          , upsert=True
                          )


if __name__ == '__main__':
    update_vote(2, "U8SNDU7UD")
