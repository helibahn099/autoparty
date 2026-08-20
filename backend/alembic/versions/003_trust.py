"""trust, reports, rotation, i18n columns

Revision ID: 003_trust
Revises: 002_geo
"""

from alembic import op

revision = "003_trust"
down_revision = "002_geo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.schema_upgrade import ensure_schema

    ensure_schema()


def downgrade() -> None:
    pass
