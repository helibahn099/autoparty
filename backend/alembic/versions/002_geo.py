"""geo + garage + batch_id

Revision ID: 002_geo
Revises: 001_initial
"""

from alembic import op

revision = "002_geo"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.schema_upgrade import ensure_schema

    ensure_schema()


def downgrade() -> None:
    pass
