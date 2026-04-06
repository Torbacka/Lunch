"""Add location to workspaces table

Revision ID: 004
Revises: 003
Create Date: 2026-04-06
"""
from alembic import op

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE workspaces ADD COLUMN location VARCHAR(64)
    """)


def downgrade():
    op.execute("ALTER TABLE workspaces DROP COLUMN location")
