"""allow null campaign_id in call_logs

Revision ID: ee076f8416dd
Revises: 0264f02a2a89
Create Date: 2026-02-27 10:40:15.043439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee076f8416dd'
down_revision: Union[str, Sequence[str], None] = '0264f02a2a89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # make campaign_id nullable so we can record calls without a campaign
    op.alter_column(
        'call_logs',
        'campaign_id',
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # revert to non-nullable column; ensure no nulls exist before applying
    op.alter_column(
        'call_logs',
        'campaign_id',
        existing_type=sa.UUID(),
        nullable=False,
    )
