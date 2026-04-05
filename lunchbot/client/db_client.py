"""PostgreSQL database client replacing mongo_client.py.

All queries use psycopg3 parameterized SQL (D-06).
Connection pool accessed via Flask app context (D-05).
"""
import json
import logging

from psycopg.rows import dict_row
from lunchbot.db import get_pool

logger = logging.getLogger(__name__)


def get_votes(poll_date):
    """Get all poll options with votes for a given date.
    Replaces mongo_client.get_votes().
    Returns list of dicts with keys: id, restaurant_id, place_id, name, rating,
    emoji, url, votes (list of user_id strings).
    """
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT po.id, po.restaurant_id, r.place_id, r.name, r.rating,
                       r.emoji, r.url, r.website, r.price_level,
                       COALESCE(
                           array_agg(v.user_id) FILTER (WHERE v.user_id IS NOT NULL),
                           '{}'
                       ) AS votes
                FROM poll_options po
                JOIN restaurants r ON r.id = po.restaurant_id
                JOIN polls p ON p.id = po.poll_id
                LEFT JOIN votes v ON v.poll_option_id = po.id
                WHERE p.poll_date = %(poll_date)s
                GROUP BY po.id, r.id
                ORDER BY po.display_order
            """, {'poll_date': poll_date})
            return cur.fetchall()


def get_all_votes():
    """Get all polls with their votes. Replaces mongo_client.get_all_votes()."""
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT p.id AS poll_id, p.poll_date, po.id AS option_id,
                       r.place_id, r.name,
                       COALESCE(
                           array_agg(v.user_id) FILTER (WHERE v.user_id IS NOT NULL),
                           '{}'
                       ) AS votes
                FROM polls p
                JOIN poll_options po ON po.poll_id = p.id
                JOIN restaurants r ON r.id = po.restaurant_id
                LEFT JOIN votes v ON v.poll_option_id = po.id
                GROUP BY p.id, po.id, r.id
                ORDER BY p.poll_date DESC, po.display_order
            """)
            return cur.fetchall()


def toggle_vote(poll_option_id, user_id):
    """Toggle a vote: DELETE if exists, INSERT if not. Per D-04.
    Replaces mongo_client.update_vote().
    Returns 'added' or 'removed' to indicate what happened.
    """
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM votes WHERE poll_option_id = %(option_id)s AND user_id = %(user_id)s RETURNING id",
                {'option_id': poll_option_id, 'user_id': user_id}
            )
            if cur.fetchone() is not None:
                logger.info('Vote removed: option=%s user=%s', poll_option_id, user_id)
                return 'removed'
            cur.execute(
                "INSERT INTO votes (poll_option_id, user_id) VALUES (%(option_id)s, %(user_id)s)",
                {'option_id': poll_option_id, 'user_id': user_id}
            )
            logger.info('Vote added: option=%s user=%s', poll_option_id, user_id)
            return 'added'


def upsert_suggestion(poll_date, restaurant_id, workspace_id=None):
    """Add a restaurant as a poll option for today. Replaces mongo_client.update_suggestions().
    Creates poll if it doesn't exist, then adds restaurant as option.
    """
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Upsert poll for this date
            cur.execute("""
                INSERT INTO polls (poll_date, workspace_id)
                VALUES (%(poll_date)s, %(workspace_id)s)
                ON CONFLICT (poll_date, workspace_id) DO UPDATE SET poll_date = EXCLUDED.poll_date
                RETURNING id
            """, {'poll_date': poll_date, 'workspace_id': workspace_id})
            poll = cur.fetchone()
            poll_id = poll['id']

            # Get next display order
            cur.execute(
                "SELECT COALESCE(MAX(display_order), -1) + 1 AS next_order FROM poll_options WHERE poll_id = %(poll_id)s",
                {'poll_id': poll_id}
            )
            next_order = cur.fetchone()['next_order']

            # Add restaurant as poll option
            cur.execute("""
                INSERT INTO poll_options (poll_id, restaurant_id, display_order)
                VALUES (%(poll_id)s, %(restaurant_id)s, %(display_order)s)
                ON CONFLICT (poll_id, restaurant_id) DO NOTHING
            """, {'poll_id': poll_id, 'restaurant_id': restaurant_id, 'display_order': next_order})

            return poll_id


def save_restaurant(restaurant):
    """Upsert a restaurant from Google Places API response.
    Replaces mongo_client.save_restaurants_info() for single restaurant.
    Returns the restaurant id.
    """
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                INSERT INTO restaurants (place_id, name, rating, price_level, geometry, photos,
                    opening_hours, icon, vicinity, types, user_ratings_total)
                VALUES (%(place_id)s, %(name)s, %(rating)s, %(price_level)s, %(geometry)s,
                    %(photos)s, %(opening_hours)s, %(icon)s, %(vicinity)s, %(types)s,
                    %(user_ratings_total)s)
                ON CONFLICT (place_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    rating = EXCLUDED.rating,
                    price_level = EXCLUDED.price_level,
                    geometry = EXCLUDED.geometry,
                    photos = EXCLUDED.photos,
                    opening_hours = EXCLUDED.opening_hours,
                    icon = EXCLUDED.icon,
                    vicinity = EXCLUDED.vicinity,
                    types = EXCLUDED.types,
                    user_ratings_total = EXCLUDED.user_ratings_total,
                    updated_at = NOW()
                RETURNING id
            """, {
                'place_id': restaurant['place_id'],
                'name': restaurant['name'],
                'rating': restaurant.get('rating'),
                'price_level': restaurant.get('price_level'),
                'geometry': json.dumps(restaurant.get('geometry')) if restaurant.get('geometry') else None,
                'photos': json.dumps(restaurant.get('photos')) if restaurant.get('photos') else None,
                'opening_hours': json.dumps(restaurant.get('opening_hours')) if restaurant.get('opening_hours') else None,
                'icon': restaurant.get('icon'),
                'vicinity': restaurant.get('vicinity'),
                'types': restaurant.get('types'),
                'user_ratings_total': restaurant.get('user_ratings_total'),
            })
            result = cur.fetchone()
            return result['id']


def save_restaurants(restaurants_response):
    """Batch upsert restaurants from Google Places API search response.
    Replaces mongo_client.save_restaurants_info().
    Returns list of restaurant ids.
    """
    ids = []
    for restaurant in restaurants_response.get('results', []):
        restaurant_id = save_restaurant(restaurant)
        ids.append(restaurant_id)
    return ids


def add_emoji(place_ids, emoji_string):
    """Update emoji for multiple restaurants. Replaces mongo_client.add_emoji()."""
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE restaurants
                SET emoji = %(emoji)s, updated_at = NOW()
                WHERE place_id = ANY(%(place_ids)s)
            """, {'emoji': emoji_string, 'place_ids': place_ids})
            logger.info('Updated emoji to %s for %d restaurants', emoji_string, cur.rowcount)
            return cur.rowcount


def get_restaurant_by_place_id(place_id):
    """Get a restaurant by its Google Places place_id."""
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM restaurants WHERE place_id = %(place_id)s",
                {'place_id': place_id}
            )
            return cur.fetchone()


def update_restaurant_url(place_id, url, website):
    """Update restaurant URL and website. Replaces mongo_client.add_restaurant_url()."""
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                UPDATE restaurants
                SET url = %(url)s, website = %(website)s, updated_at = NOW()
                WHERE place_id = %(place_id)s
                RETURNING *
            """, {'url': url, 'website': website, 'place_id': place_id})
            return cur.fetchone()
