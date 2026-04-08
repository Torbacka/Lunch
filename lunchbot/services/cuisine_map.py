"""Google Places types → human-readable cuisine labels.

Maps the 'types' array from Google Places API responses to a single
human-friendly cuisine string like "Japanese", "Burgers", "Italian".
"""

# Ordered by specificity — first match wins
_TYPE_TO_CUISINE = [
    ('bakery', 'Bakery'),
    ('cafe', 'Cafe'),
    ('bar', 'Bar'),
    ('meal_delivery', 'Delivery'),
    ('meal_takeaway', 'Takeaway'),
]

# Keyword match on restaurant name or types array (fallback after type match)
_KEYWORD_TO_CUISINE = [
    ('sushi', 'Japanese'),
    ('ramen', 'Japanese'),
    ('japanese', 'Japanese'),
    ('thai', 'Thai'),
    ('chinese', 'Chinese'),
    ('korean', 'Korean'),
    ('vietnamese', 'Vietnamese'),
    ('indian', 'Indian'),
    ('curry', 'Indian'),
    ('mexican', 'Mexican'),
    ('taco', 'Mexican'),
    ('burrito', 'Mexican'),
    ('italian', 'Italian'),
    ('pizza', 'Pizza'),
    ('pasta', 'Italian'),
    ('burger', 'Burgers'),
    ('hamburger', 'Burgers'),
    ('kebab', 'Kebab'),
    ('falafel', 'Middle Eastern'),
    ('mediterranean', 'Mediterranean'),
    ('greek', 'Greek'),
    ('french', 'French'),
    ('american', 'American'),
    ('seafood', 'Seafood'),
    ('steak', 'Steakhouse'),
    ('bbq', 'BBQ'),
    ('vegan', 'Vegan'),
    ('vegetarian', 'Vegetarian'),
    ('salad', 'Salad'),
    ('sandwich', 'Sandwiches'),
    ('soup', 'Soup'),
    ('noodle', 'Noodles'),
    ('dumpling', 'Dumplings'),
    ('poke', 'Poke'),
    ('bistro', 'Bistro'),
]


def classify_cuisine(types, name=''):
    """Derive a human-readable cuisine label from Google Places data.

    Args:
        types: list of Google Places type strings (e.g. ['restaurant', 'bar', 'food'])
        name: restaurant name for keyword matching

    Returns:
        Cuisine string (e.g. 'Japanese') or None if no match.
    """
    if not types and not name:
        return None

    types_set = set(t.lower() for t in (types or []))

    # 1. Check specific Google Places types
    for gtype, cuisine in _TYPE_TO_CUISINE:
        if gtype in types_set:
            return cuisine

    # 2. Check name + types for cuisine keywords
    search_text = (name or '').lower() + ' ' + ' '.join(types_set)
    for keyword, cuisine in _KEYWORD_TO_CUISINE:
        if keyword in search_text:
            return cuisine

    return None
