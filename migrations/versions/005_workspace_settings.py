"""Add poll settings columns to workspaces table

Revision ID: 005
Revises: 004
Create Date: 2026-04-06
"""
from alembic import op

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE workspaces ADD COLUMN poll_channel VARCHAR(64)")
    op.execute("ALTER TABLE workspaces ADD COLUMN poll_schedule_time TIME")
    op.execute("ALTER TABLE workspaces ADD COLUMN poll_schedule_timezone VARCHAR(64)")
    op.execute("ALTER TABLE workspaces ADD COLUMN poll_schedule_weekdays TEXT[]")
    op.execute("ALTER TABLE workspaces ADD COLUMN poll_size INTEGER")
    op.execute("ALTER TABLE workspaces ADD COLUMN smart_picks INTEGER")


def downgrade():
    op.execute("ALTER TABLE workspaces DROP COLUMN smart_picks")
    op.execute("ALTER TABLE workspaces DROP COLUMN poll_size")
    op.execute("ALTER TABLE workspaces DROP COLUMN poll_schedule_weekdays")
    op.execute("ALTER TABLE workspaces DROP COLUMN poll_schedule_timezone")
    op.execute("ALTER TABLE workspaces DROP COLUMN poll_schedule_time")
    op.execute("ALTER TABLE workspaces DROP COLUMN poll_channel")
