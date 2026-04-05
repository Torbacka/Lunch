from flask import current_app


def get_pool():
    """Get the psycopg3 ConnectionPool from Flask app extensions."""
    return current_app.extensions['pool']
