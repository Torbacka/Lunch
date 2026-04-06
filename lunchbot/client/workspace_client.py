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
