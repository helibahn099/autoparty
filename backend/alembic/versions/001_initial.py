"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-08-18
"""

from alembic import op  # noqa: F401

from app.database import Base, engine
from app import models  # noqa: F401

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=engine)


def downgrade() -> None:
    Base.metadata.drop_all(bind=engine)
