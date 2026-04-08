"""Add cuisine, walking_minutes, pick_type to poll_options

Revision ID: 006
Revises: 005
Create Date: 2026-04-08
"""
from alembic import op

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE poll_options ADD COLUMN cuisine VARCHAR(64)")
    op.execute("ALTER TABLE poll_options ADD COLUMN walking_minutes SMALLINT")
    op.execute("ALTER TABLE poll_options ADD COLUMN pick_type VARCHAR(16) DEFAULT 'random'")


def downgrade():
    op.execute("ALTER TABLE poll_options DROP COLUMN pick_type")
    op.execute("ALTER TABLE poll_options DROP COLUMN walking_minutes")
    op.execute("ALTER TABLE poll_options DROP COLUMN cuisine")
