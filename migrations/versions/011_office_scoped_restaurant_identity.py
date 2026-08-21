"""office-scoped restaurant identity and custom restaurants

Revision ID: 011
Revises: 010
Create Date: 2026-08-21
"""
from alembic import op


revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE restaurants ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'google'")
    op.execute("ALTER TABLE restaurants ADD COLUMN normalized_name TEXT")
    op.execute("""
        ALTER TABLE restaurants
        ADD CONSTRAINT restaurants_source_check
        CHECK (source IN ('google', 'custom'))
    """)
    op.execute("ALTER TABLE restaurants DROP CONSTRAINT restaurants_place_id_key")
    op.execute("""
        ALTER TABLE restaurants
        ADD CONSTRAINT restaurants_workspace_location_place_key
        UNIQUE (workspace_id, location_id, place_id)
    """)
    op.execute("""
        CREATE UNIQUE INDEX restaurants_custom_office_name_key
        ON restaurants (workspace_id, location_id, normalized_name)
        WHERE source = 'custom'
    """)


def downgrade():
    raise NotImplementedError(
        '011 allows duplicate place_id values across offices; restore from backup to revert'
    )
