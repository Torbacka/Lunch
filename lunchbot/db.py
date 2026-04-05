from flask import current_app, g
from psycopg.rows import dict_row


def get_pool():
    """Get the psycopg3 ConnectionPool from Flask app extensions."""
    return current_app.extensions['pool']


def execute_with_tenant(sql, params=None, *, fetch='all'):
    """Execute SQL with tenant context from g.workspace_id.

    Sets app.current_tenant on the connection before executing.
    fetch: 'all' returns list of dicts, 'one' returns single dict or None, 'none' returns None (for INSERT/UPDATE/DELETE).
    """
    workspace_id = getattr(g, 'workspace_id', None)
    with get_pool().connection() as conn:
        if workspace_id:
            # PostgreSQL SET does not support parameterized values ($1 syntax);
            # workspace_id comes from Slack team_id (alphanumeric, no injection risk)
            conn.execute(f"SET app.current_tenant = '{workspace_id}'")
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            if fetch == 'all':
                return cur.fetchall()
            elif fetch == 'one':
                return cur.fetchone()
            elif fetch == 'none':
                return None
            return cur.fetchall()
