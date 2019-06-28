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
    restaurants = {
        "html_attributions": [],
        "results": [
            {
                "geometry": {
                    "location": {
                        "lat": 59.33976529999999,
                        "lng": 18.0627921
                    },
                    "viewport": {
                        "northeast": {
                            "lat": 59.34111947989272,
                            "lng": 18.06417287989272
                        },
                        "southwest": {
                            "lat": 59.33841982010728,
                            "lng": 18.06147322010727
                        }
                    }
                },
                "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
                "id": "8dd3be76faf68c74a3c1b8cdc5e541a1e6f1b15b",
                "name": "Tre Kronor",
                "opening_hours": {
                    "open_now": False
                },
                "photos": [
                    {
                        "height": 2610,
                        "html_attributions": [
                            "<a href=\"https://maps.google.com/maps/contrib/109068798380843980081/photos\">Tomas Echeverri Valencia</a>"
                        ],
                        "photo_reference": "CmRaAAAAQ9ti8NjhPGepk65BbrR1wIpinP5kmTFtuhAl--ank3t2igIxdrQ3PtoFSI8HrmTl5kI9F5VCiSLKtg6xYBj-l2eo6P42rNFVRZLq4fYFT3-_T_YJsLrrMJvvsDq8cjbKEhBVz9oEudncKfwELsaA-Sq_GhSyBtJttQV6JtkNb1yAz_Ko0oNaNg",
                        "width": 4640
                    }
                ],
                "place_id": "ChIJR4pFcGidX0YRspb4Pd8sS7Y",
                "plus_code": {
                    "compound_code": "83Q7+W4 Stockholm, Sweden",
                    "global_code": "9FFW83Q7+W4"
                },
                "rating": 3.7,
                "reference": "ChIJR4pFcGidX0YRspb4Pd8sS7Y",
                "types": [
                    "restaurant",
                    "food",
                    "point_of_interest",
                    "establishment"
                ],
                "user_ratings_total": 61,
                "vicinity": "Döbelnsgatan 6, Stockholm"
            },
            {
                "geometry": {
                    "location": {
                        "lat": 59.3373603,
                        "lng": 18.0621361
                    },
                    "viewport": {
                        "northeast": {
                            "lat": 59.33867012989271,
                            "lng": 18.06333107989272
                        },
                        "southwest": {
                            "lat": 59.33597047010727,
                            "lng": 18.06063142010728
                        }
                    }
                },
                "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
                "id": "ac3c6c0fb664b9a505ca53a21b2fec9a6a48f1c9",
                "name": "Giro",
                "opening_hours": {
                    "open_now": False
                },
                "photos": [
                    {
                        "height": 2610,
                        "html_attributions": [
                            "<a href=\"https://maps.google.com/maps/contrib/108242777176578549631/photos\">James Tucker</a>"
                        ],
                        "photo_reference": "CmRaAAAA4u_yCWC8oEuJ8w7eV7MTJbghNxnze3-SFNMQXLv-CvVd2ieZzIg1uj8uZDoL2zZuY_1oJTrHuIylmw5tNvi2xloiPg5PTS5ppkPhRupZUptbyKBodSOuodDWyBvBMgaJEhDnJHI92JeP2V4ZeMKNfSRMGhR2qqU5YI_VXhoyWPoSq_Nv1ZsUlw",
                        "width": 4640
                    }
                ],
                "place_id": "ChIJP5KQvWedX0YR_q0tl0igws0",
                "plus_code": {
                    "compound_code": "83P6+WV Stockholm, Sweden",
                    "global_code": "9FFW83P6+WV"
                },
                "rating": 4.2,
                "reference": "ChIJP5KQvWedX0YR_q0tl0igws0",
                "scope": "GOOGLE",
                "types": [
                    "restaurant",
                    "food",
                    "point_of_interest",
                    "establishment"
                ],
                "user_ratings_total": 859,
                "vicinity": "Sveavägen 46, Stockholm"
            },
            {
                "geometry": {
                    "location": {
                        "lat": 59.34595389999999,
                        "lng": 18.0599579
                    },
                    "viewport": {
                        "northeast": {
                            "lat": 59.34732977989272,
                            "lng": 18.06121717989272
                        },
                        "southwest": {
                            "lat": 59.34463012010727,
                            "lng": 18.05851752010728
                        }
                    }
                },
                "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
                "id": "14c9a4eba33e2d89e73023e9aeb742feb898817d",
                "name": "Montebello",
                "opening_hours": {
                    "open_now": False
                },
                "photos": [
                    {
                        "height": 3024,
                        "html_attributions": [
                            "<a href=\"https://maps.google.com/maps/contrib/111185898406633600052/photos\">Pontus Thedvall</a>"
                        ],
                        "photo_reference": "CmRaAAAAroG8BJAprl_RAOohXqZI2VOcViMb23ZCdrb8YOcPAtgiUK_zCCGrovZBU1O-VHF-yR0lQETLnj12-ib1GGcMeL6NY_nLpy9T1njHzOSxeMF7TN_5fwbmX4L9zGudKj7fEhDaLygtA-69IgKCvSYNPQZOGhQ32tkoKnOX7s2bKR8cYsLkGNwQGA",
                        "width": 4032
                    }
                ],
                "place_id": "ChIJlfr5A2ydX0YRnD0ztWdBPVI",
                "plus_code": {
                    "compound_code": "83W5+9X Stockholm, Sweden",
                    "global_code": "9FFW83W5+9X"
                },
                "price_level": 1,
                "rating": 4.1,
                "reference": "ChIJlfr5A2ydX0YRnD0ztWdBPVI",
                "scope": "GOOGLE",
                "types": [
                    "restaurant",
                    "food",
                    "point_of_interest",
                    "establishment"
                ],
                "user_ratings_total": 66,
                "vicinity": "Surbrunnsgatan 25, Stockholm"
            },
            {
                "geometry": {
                    "location": {
                        "lat": 59.3372123,
                        "lng": 18.0537877
                    },
                    "viewport": {
                        "northeast": {
                            "lat": 59.33857412989272,
                            "lng": 18.05518442989272
                        },
                        "southwest": {
                            "lat": 59.33587447010727,
                            "lng": 18.05248477010728
                        }
                    }
                },
                "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
                "id": "790a5b50995148b295a88570bb38b177aa1792bd",
                "name": "Pizza Hatt",
                "opening_hours": {
                    "open_now": False
                },
                "photos": [
                    {
                        "height": 2160,
                        "html_attributions": [
                            "<a href=\"https://maps.google.com/maps/contrib/108016375285079607990/photos\">Elin Lundström Ekman</a>"
                        ],
                        "photo_reference": "CmRaAAAAiWJsndlwe3XrhamzNE3vpYeFLhzftKZe3jV66xbLemnQ5YbwqkEGO8IH_nGWx078H2p53tOp9OcM9F01zp0xj4yhqDFV6g5dawqlHGge2frW_dA3YwxnNP1uMn2HDKlkEhBgxPFhukKab0Qm1YlMRqrNGhTyI6NOiPPRbCG9-cmYeJz-Hh4IBQ",
                        "width": 3840
                    }
                ],
                "place_id": "ChIJoZAkKmSdX0YR6jeM3q1ID6c",
                "plus_code": {
                    "compound_code": "83P3+VG Stockholm, Sweden",
                    "global_code": "9FFW83P3+VG"
                },
                "price_level": 2,
                "rating": 4.6,
                "reference": "ChIJoZAkKmSdX0YR6jeM3q1ID6c",
                "types": [
                    "restaurant",
                    "food",
                    "point_of_interest",
                    "establishment"
                ],
                "user_ratings_total": 267,
                "vicinity": "Upplandsgatan 9A, Stockholm"
            },
            {
                "geometry": {
                    "location": {
                        "lat": 59.34510659999999,
                        "lng": 18.0574991
                    },
                    "viewport": {
                        "northeast": {
                            "lat": 59.34643722989271,
                            "lng": 18.05877352989272
                        },
                        "southwest": {
                            "lat": 59.34373757010727,
                            "lng": 18.05607387010728
                        }
                    }
                },
                "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
                "id": "31145ed6b28a1bfc296363dc3fd9d21beefd69bf",
                "name": "Tosca pizzeria",
                "opening_hours": {
                    "open_now": False
                },
                "photos": [
                    {
                        "height": 1080,
                        "html_attributions": [
                            "<a href=\"https://maps.google.com/maps/contrib/103945533764197975758/photos\">Jesper Dahllöf</a>"
                        ],
                        "photo_reference": "CmRaAAAAbMwtsYOalM7RqIYHyZ08NJTP4R3cBjvMPxL4DmiIbwx5sBj6fxUVz4u7Xs2DyyxMg3bvH0R-vIqPyzIyebfu4mEW0XGSksnmUXcEFzdD14-4G2PVihY7G4dKuye0rUJUEhAY7unyVBIPi7dqCm4WyD-qGhTR8ZPRpkL92s-7eoDTSowqnDwBbw",
                        "width": 1920
                    }
                ],
                "place_id": "ChIJN8WYom6dX0YRq1lzLZHYN_g",
                "plus_code": {
                    "compound_code": "83W4+2X Stockholm, Sweden",
                    "global_code": "9FFW83W4+2X"
                },
                "rating": 3.6,
                "reference": "ChIJN8WYom6dX0YRq1lzLZHYN_g",
                "scope": "GOOGLE",
                "types": [
                    "restaurant",
                    "food",
                    "point_of_interest",
                    "establishment"
                ],
                "user_ratings_total": 27,
                "vicinity": "Döbelnsgatan 48, Stockholm"
            },
            {
                "geometry": {
                    "location": {
                        "lat": 59.33635839999999,
                        "lng": 18.0590827
                    },
                    "viewport": {
                        "northeast": {
                            "lat": 59.33769292989273,
                            "lng": 18.06037282989272
                        },
                        "southwest": {
                            "lat": 59.33499327010728,
                            "lng": 18.05767317010728
                        }
                    }
                },
                "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
                "id": "dadb97abc52dd17351060183308fa20fdb644e83",
                "name": "Al Forno",
                "opening_hours": {
                    "open_now": False
                },
                "photos": [
                    {
                        "height": 3016,
                        "html_attributions": [
                            "<a href=\"https://maps.google.com/maps/contrib/105210643277878658241/photos\">יניב פורת</a>"
                        ],
                        "photo_reference": "CmRaAAAAMX9DC6NohUSuUhXVEWDH374WzlXkeFPcPoC-Of8BqYPsUSaeeSz1NWjKygeJga38YRfz5gVEjO2mgclmeJMNWOCQgCtmpJOFVq1lkdtjksLo7EQKTUQV9TdlvxfRZt6_EhDC7VTSygf14K_asJRmqRUVGhS9Qw9AuJcHAXFW75M5h3y6BhZ8RA",
                        "width": 4032
                    }
                ],
                "place_id": "ChIJzRAG_2adX0YRpnNmEAL0CPw",
                "plus_code": {
                    "compound_code": "83P5+GJ Stockholm, Sweden",
                    "global_code": "9FFW83P5+GJ"
                },
                "price_level": 2,
                "rating": 3.6,
                "reference": "ChIJzRAG_2adX0YRpnNmEAL0CPw",
                "scope": "GOOGLE",
                "types": [
                    "restaurant",
                    "food",
                    "point_of_interest",
                    "establishment"
                ],
                "user_ratings_total": 547,
                "vicinity": "Drottninggatan 88 B, Stockholm"
            },
            {
                "geometry": {
                    "location": {
                        "lat": 59.3372798,
                        "lng": 18.0674753
                    },
                    "viewport": {
                        "northeast": {
                            "lat": 59.33862622989272,
                            "lng": 18.06875902989272
                        },
                        "southwest": {
                            "lat": 59.33592657010728,
                            "lng": 18.06605937010728
                        }
                    }
                },
                "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
                "id": "4a378cd59a6c2b884609da3c96e86d0735e05ed2",
                "name": "Milano",
                "opening_hours": {
                    "open_now": False
                },
                "photos": [
                    {
                        "height": 3968,
                        "html_attributions": [
                            "<a href=\"https://maps.google.com/maps/contrib/100726461273186789543/photos\">A Google User</a>"
                        ],
                        "photo_reference": "CmRaAAAAFx4QFOMew5jHCJ7UwYmCZDqQ_aIo5PeUQjDs5C5_uh6LHuC48JYWV3D7kUqEoM0MfSpb37WBIuqijSFAOBQpGKu1k6TR4ZdQyDTuL9q1T-IxVPv9EdaGQT5xop1Ws6guEhCHTfI37JtiyujDbsPR3jI1GhSwzOBfQ0VtwCfMyZwlnWTWeO-O3A",
                        "width": 2976
                    }
                ],
                "place_id": "ChIJjWXMOF2dX0YR7lzrzcQ0pok",
                "plus_code": {
                    "compound_code": "83P8+WX Stockholm, Sweden",
                    "global_code": "9FFW83P8+WX"
                },
                "price_level": 1,
                "rating": 3.5,
                "reference": "ChIJjWXMOF2dX0YR7lzrzcQ0pok",
                "types": [
                    "restaurant",
                    "food",
                    "point_of_interest",
                    "establishment"
                ],
                "user_ratings_total": 153,
                "vicinity": "Regeringsgatan 76, Stockholm"
            },
            {
                "geometry": {
                    "location": {
                        "lat": 59.3343345,
                        "lng": 18.0705855
                    },
                    "viewport": {
                        "northeast": {
                            "lat": 59.33563292989272,
                            "lng": 18.07194657989272
                        },
                        "southwest": {
                            "lat": 59.33293327010728,
                            "lng": 18.06924692010728
                        }
                    }
                },
                "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
                "id": "60d4d135486d5da82edb7f7b26bf257e7ab4ec58",
                "name": "Eighteen Eighty Nine Pizza",
                "opening_hours": {
                    "open_now": False
                },
                "photos": [
                    {
                        "height": 1152,
                        "html_attributions": [
                            "<a href=\"https://maps.google.com/maps/contrib/108173806632442962476/photos\">Emilio Del Tessandoro</a>"
                        ],
                        "photo_reference": "CmRaAAAAAEm_8TYY3MDm3Ds1G8azFJM-ieZqwF39e9eVDJ8tnATiqAk-xdsxosxoJZKVGPeBh0Lxyzp_9j3qfAhll7jRvTxprioR6qx3XZrORSulX5SxtMthEwKSpjtRwcZsQLQWEhCpLoBY_yV3bT8ZepD-Sa9KGhRZOUC6idfJSPmorscEhj8mhfDagw",
                        "width": 2048
                    }
                ],
                "place_id": "ChIJJVPMaFydX0YRl9R4xpPSsMQ",
                "plus_code": {
                    "compound_code": "83MC+P6 Stockholm, Sweden",
                    "global_code": "9FFW83MC+P6"
                },
                "price_level": 2,
                "rating": 4.2,
                "reference": "ChIJJVPMaFydX0YRl9R4xpPSsMQ",
                "scope": "GOOGLE",
                "types": [
                    "meal_takeaway",
                    "restaurant",
                    "food",
                    "point_of_interest",
                    "establishment"
                ],
                "user_ratings_total": 571,
                "vicinity": "Mäster Samuelsgatan 18, Stockholm"
            },
            {
                "geometry": {
                    "location": {
                        "lat": 59.3412581,
                        "lng": 18.0496124
                    },
                    "viewport": {
                        "northeast": {
                            "lat": 59.34263742989272,
                            "lng": 18.05107657989272
                        },
                        "southwest": {
                            "lat": 59.33993777010728,
                            "lng": 18.04837692010728
                        }
                    }
                },
                "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
                "id": "0f064a4ddf5a0dd1b6bcb550f028088bb55f6222",
                "name": "Crispy Pizza Bistro - Vasastan",
                "opening_hours": {
                    "open_now": False
                },
                "photos": [
                    {
                        "height": 3648,
                        "html_attributions": [
                            "<a href=\"https://maps.google.com/maps/contrib/105969898349409007490/photos\">Daniel Sundström</a>"
                        ],
                        "photo_reference": "CmRaAAAAcPKOnQZHkwpp_TP_UuBIvILCGviBtKj4Uj3u4NsS0zQFbXsctZcDsFENTIAqHuQw1avcs4HxllOZm2Tx7i0_f8VF2ZmDbDMrGFI6p6wO1q-2uaRpV_onsRnTLSnYJEiIEhCfRl_ww5nj3Qc86JFlct5PGhT4suhqfE1JzgGJgzb1AiNhi-eHKA",
                        "width": 5472
                    }
                ],
                "place_id": "ChIJx1AVi2-dX0YR4K3jiD5M_YY",
                "plus_code": {
                    "compound_code": "82RX+GR Stockholm, Sweden",
                    "global_code": "9FFW82RX+GR"
                },
                "price_level": 2,
                "rating": 4.5,
                "reference": "ChIJx1AVi2-dX0YR4K3jiD5M_YY",
                "scope": "GOOGLE",
                "types": [
                    "restaurant",
                    "food",
                    "point_of_interest",
                    "establishment"
                ],
                "user_ratings_total": 198,
                "vicinity": "Upplandsgatan 45, Stockholm"
            },
            {
                "geometry": {
                    "location": {
                        "lat": 59.3473461,
                        "lng": 18.0670128
                    },
                    "viewport": {
                        "northeast": {
                            "lat": 59.34863177989273,
                            "lng": 18.06828297989272
                        },
                        "southwest": {
                            "lat": 59.34593212010728,
                            "lng": 18.06558332010728
                        }
                    }
                },
                "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
                "id": "ade88708b24283cbcf72ce58ea09b58b84e28871",
                "name": "Dino",
                "opening_hours": {
                    "open_now": False
                },
                "photos": [
                    {
                        "height": 3264,
                        "html_attributions": [
                            "<a href=\"https://maps.google.com/maps/contrib/118146206429846050122/photos\">Brian Brenner</a>"
                        ],
                        "photo_reference": "CmRaAAAAiFHw9lu1x-jTCgA75IFm5TumsM8l3v7CCCAOKdV2_Bu4l1s-FFAlVX9jAh-Y0hBrLnR8tBLket2PO9x2dRHsb7ySkEsrJiWlZc6PpdCjfamfGrLwkSsRoYtHQAXP9EVPEhAmqRqrCBXQ9dv8Ww62VtywGhQhkzFJJoQsvPOXAZIYB-IoX4TG8w",
                        "width": 2448
                    }
                ],
                "place_id": "ChIJKfkyVWqdX0YRuAUVM24oLLI",
                "plus_code": {
                    "compound_code": "83W8+WR Stockholm, Sweden",
                    "global_code": "9FFW83W8+WR"
                },
                "price_level": 1,
                "rating": 4,
                "reference": "ChIJKfkyVWqdX0YRuAUVM24oLLI",
                "scope": "GOOGLE",
                "types": [
                    "restaurant",
                    "food",
                    "point_of_interest",
                    "establishment"
                ],
                "user_ratings_total": 188,
                "vicinity": "Valhallavägen 53, Stockholm"
            },
            {
                "geometry": {
                    "location": {
                        "lat": 59.34940839999999,
                        "lng": 18.0587044
                    },
                    "viewport": {
                        "northeast": {
                            "lat": 59.35080067989271,
                            "lng": 18.06021467989272
                        },
                        "southwest": {
                            "lat": 59.34810102010727,
                            "lng": 18.05751502010728
                        }
                    }
                },
                "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
                "name": "Don Corleone",
                "opening_hours": {
                    "open_now": False
                },
                "photos": [
                    {
                        "height": 3456,
                        "html_attributions": [
                            "<a href=\"https://maps.google.com/maps/contrib/113258858304342105498/photos\">Adam Skärbo Jonsson</a>"
                        ],
                        "photo_reference": "CmRaAAAATg_6ZlA6WEfkM8_hjO8VhvXrjjXKQq9IEU_RBNygx4U2gibPh4_mFFGyMqfaBV2QR1bIpQ4rTYTZv_6-qQ9ewlhPrDma7rj_TqHikzSiSz9i80rSLR0xLpSnJC2QTdi9EhB2zef2HBLMFRftpnZ4TdSKGhRg-Lje3XbYNUYjvgjt1LKLkY4Ekg",
                        "width": 4608
                    }
                ],
                "place_id": "ChIJv8JS42ydX0YRS3lcAjuG-lY",
                "plus_code": {
                    "compound_code": "83X5+QF Stockholm, Sweden",
                    "global_code": "9FFW83X5+QF"
                },
                "price_level": 1,
                "rating": 4.1,
                "reference": "ChIJv8JS42ydX0YRS3lcAjuG-lY",
                "scope": "GOOGLE",
                "types": [
                    "restaurant",
                    "food",
                    "point_of_interest",
                    "establishment"
                ],
                "user_ratings_total": 102,
                "vicinity": "Birger Jarlsgatan 115A, Stockholm"
            },
            {
                "geometry": {
                    "location": {
                        "lat": 59.346534,
                        "lng": 18.059412
                    },
                    "viewport": {
                        "northeast": {
                            "lat": 59.34793342989272,
                            "lng": 18.06095037989272
                        },
                        "southwest": {
                            "lat": 59.34523377010728,
                            "lng": 18.05825072010727
                        }
                    }
                },
                "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
                "id": "5fae6875d79948002089693eed8abf24b0897366",
                "name": "Meno Male Vasastan",
                "opening_hours": {
                    "open_now": False
                },
                "photos": [
                    {
                        "height": 4128,
                        "html_attributions": [
                            "<a href=\"https://maps.google.com/maps/contrib/106343570662616468781/photos\">Margareta Elensky</a>"
                        ],
                        "photo_reference": "CmRaAAAAKvFR0T3Z-dLa1k1DnAfdfMQS21edNVy4YHTkAZR4Hd5nKoBP7ri9sONmXQuuoxwRl84THoqC69P5qYbPwNI_f3Gh_FjDfGhNxebUfN0x1oSWhlGYPxLpVcFmGerD5TR2EhDBQW5AiNlDl1f_kV7CyKALGhTzLupurO37dSLnX5ZIDpMpw2hVOg",
                        "width": 2322
                    }
                ],
                "place_id": "ChIJ__8bEWydX0YRZ53-d0OiSMo",
                "plus_code": {
                    "compound_code": "83W5+JQ Stockholm, Sweden",
                    "global_code": "9FFW83W5+JQ"
                },
                "price_level": 2,
                "rating": 4.6,
                "reference": "ChIJ__8bEWydX0YRZ53-d0OiSMo",
                "scope": "GOOGLE",
                "types": [
                    "restaurant",
                    "food",
                    "point_of_interest",
                    "establishment"
                ],
                "user_ratings_total": 730,
                "vicinity": "Roslagsgatan 15, Stockholm"
            },
            {
                "geometry": {
                    "location": {
                        "lat": 59.34155459999999,
                        "lng": 18.0587888
                    },
                    "viewport": {
                        "northeast": {
                            "lat": 59.34294367989273,
                            "lng": 18.06009947989272
                        },
                        "southwest": {
                            "lat": 59.34024402010728,
                            "lng": 18.05739982010728
                        }
                    }
                },
                "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/restaurant-71.png",
                "id": "c27d940b3be6b37c322dffdc81bca713f7426313",
                "name": "Pizzeria Buona Sera",
                "opening_hours": {
                    "open_now": False
                },
                "photos": [
                    {
                        "height": 4608,
                        "html_attributions": [
                            "<a href=\"https://maps.google.com/maps/contrib/105786599051955238023/photos\">Robert Gustafsson</a>"
                        ],
                        "photo_reference": "CmRaAAAAB2qbBAQX5eidLye0QV7pKQpKvN5XAn4uxX6bSCrIUHkINHXHSZefDzSsoId5mr98tSAFbm5zlchAAax1UWDCj4ghWy4z0B_aiu-QLj99dvA_ifGdKVNd9A-u61Vv_YceEhD-pS2F7Q8KBjDpB6D35ro4GhRVRryRK0FDv9eHIwp59qh6rqqgkA",
                        "width": 3456
                    }
                ],
                "place_id": "ChIJ9Qb9xWidX0YRiE_Ssr_FQWU",
                "plus_code": {
                    "compound_code": "83R5+JG Stockholm, Sweden",
                    "global_code": "9FFW83R5+JG"
                },
                "price_level": 1,
                "rating": 4,
                "reference": "ChIJ9Qb9xWidX0YRiE_Ssr_FQWU",
                "scope": "GOOGLE",
                "types": [
                    "restaurant",
                    "food",
                    "point_of_interest",
                    "establishment"
                ],
                "user_ratings_total": 214,
                "vicinity": "Kungstensgatan 35, Stockholm"
            }
        ],
        "status": "OK"
    }
    save_restaurants_info(restaurants)
