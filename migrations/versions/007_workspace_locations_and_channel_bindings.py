"""Workspace locations and per-channel location bindings.

Introduces two new tables:
  workspace_locations   -- named office locations for a workspace (many per team)
  channel_locations     -- pins one workspace_location per Slack channel

Backfills one 'Default' workspace_locations row per workspace with a non-null
legacy workspaces.location value. The workspaces.location column is NOT dropped;
it is kept for rollback safety and is deprecated -- no new code should read it.

Revision ID: 007
Revises: 006
Create Date: 2026-04-15
"""
from alembic import op

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    # workspace_locations: named offices per workspace
    op.execute("""
        CREATE TABLE workspace_locations (
            id SERIAL PRIMARY KEY,
            team_id VARCHAR(64) NOT NULL REFERENCES workspaces(team_id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            lat_lng VARCHAR(64) NOT NULL,
            is_default BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (team_id, name)
        )
    """)
    op.execute("CREATE INDEX idx_workspace_locations_team_id ON workspace_locations(team_id)")

    # channel_locations: per-channel binding to one workspace_location
    op.execute("""
        CREATE TABLE channel_locations (
            team_id VARCHAR(64) NOT NULL,
            channel_id VARCHAR(64) NOT NULL,
            location_id INTEGER NOT NULL REFERENCES workspace_locations(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (team_id, channel_id)
        )
    """)

    # Grant DML on the new tables + sequence to the lunchbot_app role
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'lunchbot_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON workspace_locations TO lunchbot_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON channel_locations TO lunchbot_app;
                GRANT USAGE, SELECT ON SEQUENCE workspace_locations_id_seq TO lunchbot_app;
            END IF;
        END
        $$
    """)

    # RLS: tenant isolation matching the migration 002 pattern
    # (USING workspace_id = current_setting('app.current_tenant', true))
    # Here the tenant column is team_id -- compare against the same GUC.
    for table in ('workspace_locations', 'channel_locations'):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            FOR ALL
            USING (team_id = current_setting('app.current_tenant', true))
            WITH CHECK (team_id = current_setting('app.current_tenant', true))
        """)

    # Backfill: one 'Default' workspace_locations row per workspace with a
    # non-null legacy location. is_default=true so the resolver can auto-bind
    # silently for single-location installs.
    op.execute("""
        INSERT INTO workspace_locations (team_id, name, lat_lng, is_default)
        SELECT team_id, 'Default', location, TRUE
        FROM workspaces
        WHERE location IS NOT NULL AND location <> ''
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS channel_locations")
    op.execute("DROP TABLE IF EXISTS workspace_locations")
