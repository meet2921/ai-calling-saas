"""add_missing_indexes

Revision ID: dbefe2f699d8
Revises: cb6d2d6ceb84
Create Date: 2026-03-24 09:53:43.159308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dbefe2f699d8'
down_revision: Union[str, Sequence[str], None] = 'cb6d2d6ceb84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing indexes for high-frequency query columns."""
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=False)

    # call_logs — queried by campaign, lead, and ordered by created_at in analytics
    op.create_index('ix_call_logs_campaign_id', 'call_logs', ['campaign_id'], unique=False)
    op.create_index('ix_call_logs_lead_id',     'call_logs', ['lead_id'],     unique=False)
    op.create_index('ix_call_logs_created_at',  'call_logs', ['created_at'],  unique=False)

    # leads — filtered by status constantly during campaign execution
    op.create_index('ix_leads_status', 'leads', ['status'], unique=False)

    # users — looked up by org on every auth check
    op.create_index('ix_users_organization_id', 'users', ['organization_id'], unique=False)

    # campaigns — listed per org on dashboard and analytics
    op.create_index('ix_campaigns_organization_id', 'campaigns', ['organization_id'], unique=False)

    # wallet_transactions — listed per wallet, ordered by created_at
    op.create_index('ix_wallet_transactions_wallet_id',  'wallet_transactions', ['wallet_id'],  unique=False)
    op.create_index('ix_wallet_transactions_created_at', 'wallet_transactions', ['created_at'], unique=False)


def downgrade() -> None:
    """Remove added indexes."""
    op.drop_index('ix_wallet_transactions_created_at', table_name='wallet_transactions')
    op.drop_index('ix_wallet_transactions_wallet_id',  table_name='wallet_transactions')
    op.drop_index('ix_campaigns_organization_id',      table_name='campaigns')
    op.drop_index('ix_users_organization_id',          table_name='users')
    op.drop_index('ix_leads_status',                   table_name='leads')
    op.drop_index('ix_call_logs_created_at',           table_name='call_logs')
    op.drop_index('ix_call_logs_lead_id',              table_name='call_logs')
    op.drop_index('ix_call_logs_campaign_id',          table_name='call_logs')
    op.drop_index('ix_organizations_slug',             table_name='organizations')
