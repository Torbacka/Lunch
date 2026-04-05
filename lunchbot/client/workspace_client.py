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
