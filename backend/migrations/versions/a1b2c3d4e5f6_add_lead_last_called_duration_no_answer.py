"""add lead last_called duration and no_answer status

Revision ID: a1b2c3d4e5f6
Revises: 292bd4a5b59e
Create Date: 2026-03-25 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '292bd4a5b59e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add no_answer to lead_status enum
    op.execute("ALTER TYPE lead_status ADD VALUE IF NOT EXISTS 'no_answer'")

    # Add last_called and duration columns to leads
    op.add_column('leads', sa.Column('last_called', sa.DateTime(), nullable=True))
    op.add_column('leads', sa.Column('duration', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('leads', 'duration')
    op.drop_column('leads', 'last_called')
    # Note: PostgreSQL does not support removing enum values
