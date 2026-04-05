"""Multi-tenancy: workspaces table, workspace_id denormalization, RLS policies

Revision ID: 002
Revises: 001
Create Date: 2026-04-05
"""
from alembic import op

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create workspaces table (not subject to RLS -- admin table)
    op.execute("""
        CREATE TABLE workspaces (
            id SERIAL PRIMARY KEY,
            team_id VARCHAR(64) UNIQUE NOT NULL,
            team_name VARCHAR(255),
            bot_token_encrypted TEXT NOT NULL,
            bot_user_id VARCHAR(64),
            scopes TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            installed_at TIMESTAMPTZ DEFAULT NOW(),
            uninstalled_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Add workspace_id to poll_options and votes for direct RLS
    op.execute("ALTER TABLE poll_options ADD COLUMN workspace_id VARCHAR(64)")
    op.execute("ALTER TABLE votes ADD COLUMN workspace_id VARCHAR(64)")

    # Make workspace_id NOT NULL on restaurants and polls
    # (Phase 1 left it nullable; no production data exists)
    op.execute("ALTER TABLE restaurants ALTER COLUMN workspace_id SET DEFAULT ''")
    op.execute("ALTER TABLE restaurants ALTER COLUMN workspace_id SET NOT NULL")
    op.execute("ALTER TABLE polls ALTER COLUMN workspace_id SET DEFAULT ''")
    op.execute("ALTER TABLE polls ALTER COLUMN workspace_id SET NOT NULL")

    # Create application role for non-superuser connections (RLS enforcement)
    # FORCE ROW LEVEL SECURITY is set but superusers still bypass it.
    # lunchbot_app is a non-superuser role used by the app and RLS tests.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lunchbot_app') THEN
                CREATE ROLE lunchbot_app LOGIN PASSWORD 'lunchbot_app_dev';
            END IF;
        END
        $$
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lunchbot_app")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO lunchbot_app")

    # Enable RLS and create tenant isolation policies on all four tenant tables
    for table in ['restaurants', 'polls', 'poll_options', 'votes']:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            FOR ALL
            USING (workspace_id = current_setting('app.current_tenant', true))
            WITH CHECK (workspace_id = current_setting('app.current_tenant', true))
        """)


def downgrade():
    # Drop policies and disable RLS on all four tenant tables
    for table in ['restaurants', 'polls', 'poll_options', 'votes']:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Revoke permissions from application role in this database.
    # Note: DROP ROLE is intentionally omitted -- roles are cluster-level
    # and may be in use by other databases. Upgrade is idempotent (IF NOT EXISTS).
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'lunchbot_app') THEN
                REVOKE ALL ON ALL TABLES IN SCHEMA public FROM lunchbot_app;
                REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM lunchbot_app;
                DROP OWNED BY lunchbot_app;
            END IF;
        END
        $$
    """)

    # Make workspace_id nullable again on restaurants and polls
    op.execute("ALTER TABLE restaurants ALTER COLUMN workspace_id DROP NOT NULL")
    op.execute("ALTER TABLE restaurants ALTER COLUMN workspace_id DROP DEFAULT")
    op.execute("ALTER TABLE polls ALTER COLUMN workspace_id DROP NOT NULL")
    op.execute("ALTER TABLE polls ALTER COLUMN workspace_id DROP DEFAULT")

    # Drop workspace_id from poll_options and votes
    op.execute("ALTER TABLE poll_options DROP COLUMN workspace_id")
    op.execute("ALTER TABLE votes DROP COLUMN workspace_id")

    # Drop workspaces table
    op.execute("DROP TABLE IF EXISTS workspaces")
