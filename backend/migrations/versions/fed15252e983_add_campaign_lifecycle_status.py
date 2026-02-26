"""add campaign lifecycle status

Revision ID: fed15252e983
Revises: 85bf09c1b88d
Create Date: 2026-02-24 16:02:16.786354
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fed15252e983'
down_revision: Union[str, Sequence[str], None] = '85bf09c1b88d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 1️⃣ Create ENUM type first
    campaign_status = postgresql.ENUM(
        'draft',
        'scheduled',
        'running',
        'paused',
        'completed',
        'stopped',
        name='campaign_status'
    )

    campaign_status.create(op.get_bind())

    # 2️⃣ Add new columns
    op.add_column(
        'campaigns',
        sa.Column(
            'status',
            campaign_status,
            nullable=False,
            server_default='draft'   # important if table already has data
        )
    )

    op.add_column(
        'campaigns',
        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=True
        )
    )

    # 3️⃣ Drop old is_active column
    op.drop_column('campaigns', 'is_active')


def downgrade() -> None:
    """Downgrade schema."""

    # 1️⃣ Recreate is_active column
    op.add_column(
        'campaigns',
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=True
        )
    )

    # 2️⃣ Drop new columns
    op.drop_column('campaigns', 'updated_at')
    op.drop_column('campaigns', 'status')

    # 3️⃣ Drop ENUM type
    postgresql.ENUM(
        name='campaign_status'
    ).drop(op.get_bind())