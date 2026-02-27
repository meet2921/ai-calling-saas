"""make user_number nullable in call_logs

Revision ID: f8b2f8c9a1b3
Revises: ee076f8416dd
Create Date: 2026-02-27 10:51:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8b2f8c9a1b3'
down_revision: Union[str, Sequence[str], None] = 'ee076f8416dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # make user_number nullable to support incomplete webhook payloads
    op.alter_column(
        'call_logs',
        'user_number',
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # revert to non-nullable column; ensure no nulls exist before applying
    op.alter_column(
        'call_logs',
        'user_number',
        existing_type=sa.String(),
        nullable=False,
    )
