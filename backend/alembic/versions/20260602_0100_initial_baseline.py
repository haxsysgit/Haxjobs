"""create initial migration baseline

Revision ID: 20260602_0100
Revises: 
Create Date: 2026-06-02 09:30:00
"""
from typing import Sequence, Union

revision: str = "20260602_0100"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0.1.1 only establishes the migration pipeline. Core tables arrive in 0.1.2.
    pass


def downgrade() -> None:
    pass
