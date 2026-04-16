"""office scoped candidates and channel schedules

Revision ID: 009
Revises: 008
Create Date: 2026-04-15
"""
from alembic import op

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # Step A: restaurants.location_id (D-01, D-03, D-05)
    op.execute("ALTER TABLE restaurants ADD COLUMN location_id INTEGER")
    op.execute("""
        UPDATE restaurants r
        SET location_id = wl.id
        FROM workspace_locations wl
        WHERE wl.team_id = r.workspace_id
          AND wl.is_default = TRUE
    """)
    op.execute("""
        DO $$
        DECLARE orphan_count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO orphan_count FROM restaurants WHERE location_id IS NULL;
            IF orphan_count > 0 THEN
                RAISE EXCEPTION '% restaurants have no default office; fix before running 009', orphan_count;
            END IF;
        END $$;
    """)
    op.execute("""
        ALTER TABLE restaurants
          ALTER COLUMN location_id SET NOT NULL,
          ADD CONSTRAINT restaurants_location_id_fkey
            FOREIGN KEY (location_id) REFERENCES workspace_locations(id) ON DELETE CASCADE
    """)
    op.execute("CREATE INDEX idx_restaurants_location_id ON restaurants(location_id)")

    # Step B: channel_schedules (D-12)
    op.execute("""
        CREATE TABLE channel_schedules (
            team_id VARCHAR(64) NOT NULL,
            channel_id VARCHAR(64) NOT NULL,
            schedule_time TIME NOT NULL,
            schedule_timezone VARCHAR(64) NOT NULL,
            schedule_weekdays VARCHAR(32) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (team_id, channel_id)
        )
    """)
    op.execute("ALTER TABLE channel_schedules ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE channel_schedules FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON channel_schedules
        FOR ALL
        USING (team_id = current_setting('app.current_tenant', true))
        WITH CHECK (team_id = current_setting('app.current_tenant', true))
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'lunchbot_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON channel_schedules TO lunchbot_app;
            END IF;
        END $$;
    """)

    # Step C: data-migrate workspace-level schedules (D-15)
    op.execute("""
        INSERT INTO channel_schedules (team_id, channel_id, schedule_time, schedule_timezone, schedule_weekdays, created_at)
        SELECT team_id, poll_channel, poll_schedule_time, poll_schedule_timezone, poll_schedule_weekdays, NOW()
        FROM workspaces
        WHERE poll_schedule_time IS NOT NULL
          AND poll_channel IS NOT NULL
        ON CONFLICT (team_id, channel_id) DO NOTHING
    """)

    # Step D: drop superseded workspaces columns (D-15)
    op.execute("ALTER TABLE workspaces DROP COLUMN IF EXISTS poll_schedule_time")
    op.execute("ALTER TABLE workspaces DROP COLUMN IF EXISTS poll_schedule_timezone")
    op.execute("ALTER TABLE workspaces DROP COLUMN IF EXISTS poll_schedule_weekdays")
    op.execute("ALTER TABLE workspaces DROP COLUMN IF EXISTS poll_channel")

    # Step E: wipe polls missing channel + set NOT NULL (D-11)
    op.execute("DELETE FROM polls WHERE slack_channel_id IS NULL")
    op.execute("ALTER TABLE polls ALTER COLUMN slack_channel_id SET NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_polls_channel_date ON polls(slack_channel_id, poll_date)")

    # Step F: drop+recreate restaurant_stats per-channel (D-02, D-04)
    op.execute("DROP TABLE IF EXISTS restaurant_stats CASCADE")
    op.execute("""
        CREATE TABLE restaurant_stats (
            channel_id VARCHAR(64) NOT NULL,
            restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
            team_id VARCHAR(64) NOT NULL,
            alpha FLOAT DEFAULT 1.0,
            beta FLOAT DEFAULT 1.0,
            times_shown INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (channel_id, restaurant_id)
        )
    """)
    op.execute("CREATE INDEX idx_restaurant_stats_restaurant_id ON restaurant_stats(restaurant_id)")
    op.execute("ALTER TABLE restaurant_stats ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE restaurant_stats FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON restaurant_stats
        FOR ALL
        USING (team_id = current_setting('app.current_tenant', true))
        WITH CHECK (team_id = current_setting('app.current_tenant', true))
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'lunchbot_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON restaurant_stats TO lunchbot_app;
            END IF;
        END $$;
    """)


def downgrade():
    raise NotImplementedError("009 is a forward-only migration; restore from backup to revert")
