"""Restaurant stats for Thompson sampling recommendations

Revision ID: 003
Revises: 002
Create Date: 2026-04-05
"""
from alembic import op

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Create restaurant_stats table for Thompson sampling parameters
    op.execute("""
        CREATE TABLE restaurant_stats (
            id SERIAL PRIMARY KEY,
            restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
            workspace_id VARCHAR(64) NOT NULL,
            alpha FLOAT DEFAULT 1.0,
            beta FLOAT DEFAULT 1.0,
            times_shown INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(restaurant_id, workspace_id)
        )
    """)

    # Enable RLS matching the exact pattern from 002_multi_tenancy.py (T-04-01)
    op.execute("ALTER TABLE restaurant_stats ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE restaurant_stats FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON restaurant_stats
        FOR ALL
        USING (workspace_id = current_setting('app.current_tenant', true))
        WITH CHECK (workspace_id = current_setting('app.current_tenant', true))
    """)

    # Grant permissions to lunchbot_app role
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON restaurant_stats TO lunchbot_app")
    op.execute("GRANT USAGE, SELECT ON restaurant_stats_id_seq TO lunchbot_app")

    # Add stats_processed_at to polls table to prevent double-processing (RESEARCH open question #1)
    op.execute("ALTER TABLE polls ADD COLUMN stats_processed_at TIMESTAMPTZ")


def downgrade():
    op.execute("ALTER TABLE polls DROP COLUMN IF EXISTS stats_processed_at")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON restaurant_stats")
    op.execute("ALTER TABLE restaurant_stats DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS restaurant_stats CASCADE")
