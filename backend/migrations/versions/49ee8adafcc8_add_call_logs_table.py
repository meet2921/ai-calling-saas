"""add call_logs table

Revision ID: 49ee8adafcc8
Revises: 69b679992d88
Create Date: 2026-02-26 14:28:13.644055

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49ee8adafcc8'
down_revision: Union[str, Sequence[str], None] = '69b679992d88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
