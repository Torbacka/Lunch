"""Drop legacy workspaces.location column.

Phase 07.1 hard cutover (D-19 / D-21). Backfills any workspaces that still
have a non-null `location` but no corresponding workspace_locations row
(edge case: workspace was created after migration 007 but before code stopped
writing the legacy column), then drops the column.

The downgrade path re-adds the column as a nullable VARCHAR(64) and
best-effort backfills it from the workspace's current default
workspace_locations row. The exact value is not guaranteed to match the
original because admins may have renamed/edited offices after migration 008
ran -- downgrade is an emergency-only operation per D-21.

Revision ID: 008
Revises: 007
Create Date: 2026-04-15
"""
from alembic import op

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # Backfill: only insert a Main Office row for workspaces whose legacy
    # location is set AND who do not yet have any workspace_locations rows.
    # The NOT EXISTS guard makes this idempotent if the migration is
    # re-applied on a half-migrated DB (T-07.1-11).
    op.execute("""
        INSERT INTO workspace_locations (team_id, name, lat_lng, is_default)
        SELECT w.team_id, 'Main Office', w.location, TRUE
        FROM workspaces w
        WHERE w.location IS NOT NULL AND w.location <> ''
          AND NOT EXISTS (
              SELECT 1 FROM workspace_locations wl WHERE wl.team_id = w.team_id
          )
    """)

    # Hard cutover: drop the column. PostgreSQL DROP COLUMN is metadata-only
    # and instantaneous on a small table (T-07.1-12).
    op.execute("ALTER TABLE workspaces DROP COLUMN location")


def downgrade():
    # Re-add nullable column and best-effort backfill from the workspace's
    # current default office (if any). The exact value is not guaranteed to
    # match the original because admins may have renamed/edited offices.
    op.execute("ALTER TABLE workspaces ADD COLUMN location VARCHAR(64)")
    op.execute("""
        UPDATE workspaces w
        SET location = wl.lat_lng
        FROM workspace_locations wl
        WHERE wl.team_id = w.team_id AND wl.is_default = TRUE
    """)
