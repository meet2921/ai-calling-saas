"""merge multiple heads

Revision ID: 6230dd9f4e5d
Revises: 13e1cc7854d6, 8662e03dfc30
Create Date: 2026-02-27 11:33:17.187078

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6230dd9f4e5d'
down_revision: Union[str, Sequence[str], None] = ('13e1cc7854d6', '8662e03dfc30')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
