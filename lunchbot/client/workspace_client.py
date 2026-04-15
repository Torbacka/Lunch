"""Workspace CRUD operations.

Workspaces table is NOT subject to RLS (admin table).
All functions use direct pool connections without tenant context.
"""
import logging
from psycopg.rows import dict_row
from lunchbot.db import get_pool

logger = logging.getLogger(__name__)


def save_workspace(team_id, team_name, bot_token_encrypted, bot_user_id, scopes):
    """Insert or update a workspace after OAuth installation.
    On conflict (team_id), updates token and reactivates.
    Returns the workspace dict.
    """
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                INSERT INTO workspaces (team_id, team_name, bot_token_encrypted, bot_user_id, scopes)
                VALUES (%(team_id)s, %(team_name)s, %(bot_token_encrypted)s, %(bot_user_id)s, %(scopes)s)
                ON CONFLICT (team_id) DO UPDATE SET
                    team_name = EXCLUDED.team_name,
                    bot_token_encrypted = EXCLUDED.bot_token_encrypted,
                    bot_user_id = EXCLUDED.bot_user_id,
                    scopes = EXCLUDED.scopes,
                    is_active = TRUE,
                    uninstalled_at = NULL,
                    updated_at = NOW()
                RETURNING *
            """, {
                'team_id': team_id,
                'team_name': team_name,
                'bot_token_encrypted': bot_token_encrypted,
                'bot_user_id': bot_user_id,
                'scopes': scopes,
            })
            result = cur.fetchone()
            logger.info('Saved workspace: %s (%s)', team_id, team_name)
            return result


def get_workspace(team_id):
    """Get workspace by Slack team_id. Returns dict or None."""
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM workspaces WHERE team_id = %(team_id)s",
                {'team_id': team_id}
            )
            return cur.fetchone()


def update_workspace_location(team_id, location):
    """Save lat,lng location string for a workspace (e.g. '59.3419,18.0645')."""
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE workspaces SET location = %(location)s, updated_at = NOW()
                WHERE team_id = %(team_id)s
            """, {'team_id': team_id, 'location': location})
            logger.info('Updated location for workspace: %s', team_id)


def get_workspace_settings(team_id):
    """Get workspace settings for App Home and scheduler.

    Returns dict with poll_channel, schedule fields, poll_size,
    smart_picks, location. None if workspace not found or inactive.

    NOTE: The `location` column is deprecated as of migration 007. New code
    must NOT read it -- use resolve_location_for_channel instead. It is
    retained in the SELECT only for rollback safety and legacy settings UI.
    """
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT team_id, poll_channel, poll_schedule_time,
                       poll_schedule_timezone, poll_schedule_weekdays,
                       poll_size, smart_picks, location
                FROM workspaces
                WHERE team_id = %(team_id)s AND is_active = TRUE
            """, {'team_id': team_id})
            return cur.fetchone()


def update_workspace_settings(team_id, **kwargs):
    """Update workspace settings columns. Only updates keys present in kwargs.

    Valid keys: poll_channel, poll_schedule_time, poll_schedule_timezone,
    poll_schedule_weekdays, poll_size, smart_picks, location.
    """
    ALLOWED = {'poll_channel', 'poll_schedule_time', 'poll_schedule_timezone',
                'poll_schedule_weekdays', 'poll_size', 'smart_picks', 'location'}
    updates = {k: v for k, v in kwargs.items() if k in ALLOWED}
    if not updates:
        return
    set_clause = ', '.join(f'{k} = %({k})s' for k in updates)
    updates['team_id'] = team_id
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE workspaces SET {set_clause}, updated_at = NOW() "
                f"WHERE team_id = %(team_id)s",
                updates
            )
            logger.info('Updated settings for workspace %s: %s', team_id, list(updates.keys()))


def _set_tenant(conn, team_id):
    """Set app.current_tenant so RLS policies on workspace_locations /
    channel_locations allow access. team_id comes from Slack and is
    alphanumeric -- safe to interpolate.
    """
    conn.execute(f"SET app.current_tenant = '{team_id}'")


def list_workspace_locations(team_id):
    """Return all workspace_locations rows for a team (ordered by id)."""
    with get_pool().connection() as conn:
        _set_tenant(conn, team_id)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT id, team_id, name, lat_lng, is_default, created_at
                FROM workspace_locations
                WHERE team_id = %(team_id)s
                ORDER BY id
            """, {'team_id': team_id})
            return cur.fetchall()


def create_workspace_location(team_id, name, lat_lng, is_default=False):
    """Insert a new workspace_location. Returns the created row."""
    with get_pool().connection() as conn:
        _set_tenant(conn, team_id)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                INSERT INTO workspace_locations (team_id, name, lat_lng, is_default)
                VALUES (%(team_id)s, %(name)s, %(lat_lng)s, %(is_default)s)
                RETURNING id, team_id, name, lat_lng, is_default, created_at
            """, {
                'team_id': team_id,
                'name': name,
                'lat_lng': lat_lng,
                'is_default': is_default,
            })
            row = cur.fetchone()
            logger.info('Created workspace_location: team=%s name=%s', team_id, name)
            return row


def get_default_location(team_id):
    """Return the is_default=true workspace_location row for a team, or None."""
    with get_pool().connection() as conn:
        _set_tenant(conn, team_id)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT id, team_id, name, lat_lng, is_default, created_at
                FROM workspace_locations
                WHERE team_id = %(team_id)s AND is_default = TRUE
                ORDER BY id
                LIMIT 1
            """, {'team_id': team_id})
            return cur.fetchone()


def get_channel_location(team_id, channel_id):
    """Return the bound workspace_location row for a channel, or None."""
    with get_pool().connection() as conn:
        _set_tenant(conn, team_id)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT wl.id, wl.team_id, wl.name, wl.lat_lng, wl.is_default, wl.created_at
                FROM channel_locations cl
                JOIN workspace_locations wl ON wl.id = cl.location_id
                WHERE cl.team_id = %(team_id)s AND cl.channel_id = %(channel_id)s
            """, {'team_id': team_id, 'channel_id': channel_id})
            return cur.fetchone()


def bind_channel_location(team_id, channel_id, location_id):
    """Upsert the channel -> location binding."""
    with get_pool().connection() as conn:
        _set_tenant(conn, team_id)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO channel_locations (team_id, channel_id, location_id)
                VALUES (%(team_id)s, %(channel_id)s, %(location_id)s)
                ON CONFLICT (team_id, channel_id) DO UPDATE SET
                    location_id = EXCLUDED.location_id
            """, {
                'team_id': team_id,
                'channel_id': channel_id,
                'location_id': location_id,
            })
            logger.info('Bound channel %s to location %s (team=%s)',
                        channel_id, location_id, team_id)


def resolve_location_for_channel(team_id, channel_id):
    """Resolve the effective workspace_location for a channel.

    Contract:
      1. If a channel binding exists -> return the joined location row.
      2. Else if the workspace has exactly one workspace_locations row ->
         auto-bind it to this channel (atomic) and return it.
      3. Else -> return None (caller must prompt the user).
    """
    with get_pool().connection() as conn:
        _set_tenant(conn, team_id)
        with conn.cursor(row_factory=dict_row) as cur:
            # 1. Existing binding
            cur.execute("""
                SELECT wl.id, wl.team_id, wl.name, wl.lat_lng, wl.is_default, wl.created_at
                FROM channel_locations cl
                JOIN workspace_locations wl ON wl.id = cl.location_id
                WHERE cl.team_id = %(team_id)s AND cl.channel_id = %(channel_id)s
            """, {'team_id': team_id, 'channel_id': channel_id})
            existing = cur.fetchone()
            if existing:
                return existing

            # 2. Single location -> auto-bind
            cur.execute("""
                SELECT id, team_id, name, lat_lng, is_default, created_at
                FROM workspace_locations
                WHERE team_id = %(team_id)s
                ORDER BY id
                LIMIT 2
            """, {'team_id': team_id})
            rows = cur.fetchall()
            if len(rows) == 1:
                only = rows[0]
                cur.execute("""
                    INSERT INTO channel_locations (team_id, channel_id, location_id)
                    VALUES (%(team_id)s, %(channel_id)s, %(location_id)s)
                    ON CONFLICT (team_id, channel_id) DO NOTHING
                """, {
                    'team_id': team_id,
                    'channel_id': channel_id,
                    'location_id': only['id'],
                })
                logger.info('Auto-bound channel %s to sole location %s (team=%s)',
                            channel_id, only['id'], team_id)
                return only

            # 3. Zero or multiple -> caller must prompt
            return None


def deactivate_workspace(team_id):
    """Soft-delete workspace on uninstall. Idempotent.
    Sets is_active=False and uninstalled_at=NOW().
    """
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE workspaces
                SET is_active = FALSE,
                    uninstalled_at = COALESCE(uninstalled_at, NOW()),
                    updated_at = NOW()
                WHERE team_id = %(team_id)s
            """, {'team_id': team_id})
            logger.info('Deactivated workspace: %s (rows=%d)', team_id, cur.rowcount)
