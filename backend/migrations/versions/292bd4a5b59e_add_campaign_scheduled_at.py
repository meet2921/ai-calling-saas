"""add_campaign_scheduled_at

Revision ID: 292bd4a5b59e
Revises: dbefe2f699d8
Create Date: 2026-03-24 10:15:08.336072

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '292bd4a5b59e'
down_revision: Union[str, Sequence[str], None] = 'dbefe2f699d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('campaigns', sa.Column('scheduled_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('campaigns', 'scheduled_at')
