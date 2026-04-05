"""Initial schema: restaurants, polls, poll_options, votes

Revision ID: 001
Revises: None
Create Date: 2026-04-05
"""
from alembic import op

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
        CREATE TABLE restaurants (
            id SERIAL PRIMARY KEY,
            place_id VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            rating NUMERIC(2,1),
            price_level SMALLINT,
            url TEXT,
            website TEXT,
            emoji VARCHAR(64),
            geometry JSONB,
            photos JSONB,
            opening_hours JSONB,
            icon TEXT,
            vicinity TEXT,
            types TEXT[],
            user_ratings_total INTEGER,
            workspace_id VARCHAR(64),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE polls (
            id SERIAL PRIMARY KEY,
            poll_date DATE NOT NULL,
            workspace_id VARCHAR(64),
            slack_channel_id VARCHAR(64),
            slack_message_ts VARCHAR(64),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(poll_date, workspace_id)
        )
    """)
    op.execute("""
        CREATE TABLE poll_options (
            id SERIAL PRIMARY KEY,
            poll_id INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
            restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
            display_order SMALLINT DEFAULT 0,
            UNIQUE(poll_id, restaurant_id)
        )
    """)
    op.execute("""
        CREATE TABLE votes (
            id SERIAL PRIMARY KEY,
            poll_option_id INTEGER NOT NULL REFERENCES poll_options(id) ON DELETE CASCADE,
            user_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(poll_option_id, user_id)
        )
    """)

def downgrade():
    op.execute("DROP TABLE IF EXISTS votes CASCADE")
    op.execute("DROP TABLE IF EXISTS poll_options CASCADE")
    op.execute("DROP TABLE IF EXISTS polls CASCADE")
    op.execute("DROP TABLE IF EXISTS restaurants CASCADE")
