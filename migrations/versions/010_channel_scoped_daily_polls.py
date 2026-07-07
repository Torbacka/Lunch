"""channel scoped daily polls

Revision ID: 010
Revises: 009
Create Date: 2026-06-16
"""
from alembic import op

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE polls DROP CONSTRAINT IF EXISTS polls_poll_date_workspace_id_key")
    op.execute("""
        ALTER TABLE polls
        ADD CONSTRAINT polls_poll_date_workspace_channel_key
        UNIQUE (poll_date, workspace_id, slack_channel_id)
    """)


def downgrade():
    op.execute("ALTER TABLE polls DROP CONSTRAINT IF EXISTS polls_poll_date_workspace_channel_key")
    op.execute("""
        ALTER TABLE polls
        ADD CONSTRAINT polls_poll_date_workspace_id_key
        UNIQUE (poll_date, workspace_id)
    """)
