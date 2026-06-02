"""create core haxjobs tables

Revision ID: 20260602_0120
Revises: 20260602_0100
Create Date: 2026-06-02 10:55:00
"""
from typing import Sequence, Union

from alembic import op

from haxjobs_api.database import Base
import haxjobs_api.models  # noqa: F401 - registers all feature model tables on Base.metadata

revision: str = "20260602_0120"
down_revision: Union[str, None] = "20260602_0100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Early 0.1.x migration: create the full feature-based model surface in one slice.
    # Later migrations should use explicit ALTER/create_table operations as the schema stabilizes.
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
