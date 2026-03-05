"""add_missing_columns_and_indexes

Revision ID: b09330f16263
Revises: 6a72c4c2f2ef
Create Date: 2026-03-03 18:07:09.085070

WHAT THIS MIGRATION DOES:
  1. organizations table:
     - Add updated_at column
     - Remove slug UNIQUE constraint (slugs are NOT globally unique in multi-tenant SaaS)
     - Add performance indexes on slug and (slug, is_active)

  2. users table:
     - Add updated_at column
     - Add last_login_at column (for audit + inactive-user cleanup)
     - Add UNIQUE index on LOWER(email) → case-insensitive global email uniqueness
     - Add composite index on (organization_id, LOWER(email)) → fast login lookup

WHY slug is NOT unique:
  Multiple companies named "Acme" must be able to register.
  Slug is a login hint/label — email is the real unique identity.

WHY LOWER(email) index:
  "User@X.com" and "user@x.com" are the same person.
  Standard UNIQUE on email column is case-sensitive and would miss this.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b09330f16263'
down_revision: Union[str, Sequence[str], None] = '6a72c4c2f2ef'   # ← points directly to original
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # =========================================================================
    # ORGANIZATIONS TABLE
    # =========================================================================

    # 1. Add updated_at (was missing from original migration)
    op.add_column(
        'organizations',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        )
    )

    # 2. Remove slug UNIQUE constraint — slugs are labels, not global identities
    #    Multiple orgs can share a slug (e.g. two companies both named "acme")
    op.drop_constraint('organizations_slug_key', 'organizations', type_='unique')

    # 3. Add performance indexes for login queries
    #    Login query: WHERE slug = ? AND is_active = true
    op.create_index('ix_organizations_slug',        'organizations', ['slug'])
    op.create_index('ix_organizations_slug_active', 'organizations', ['slug', 'is_active'])


    # =========================================================================
    # USERS TABLE
    # =========================================================================

    # 4. Add updated_at
    op.add_column(
        'users',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        )
    )

    # 5. Add last_login_at — updated on every successful login
    #    Used for: inactive-user cleanup jobs, security auditing
    op.add_column(
        'users',
        sa.Column(
            'last_login_at',
            sa.DateTime(timezone=True),
            nullable=True,
        )
    )

    # 6. CRITICAL: Case-insensitive global email uniqueness
    #    Standard op.create_index cannot create functional indexes.
    #    Must use raw SQL with LOWER(email).
    #
    #    This prevents: "User@X.com" and "user@x.com" being treated as different emails
    #    One email = one account, globally across all organizations.
    op.execute("""
        CREATE UNIQUE INDEX uq_users_email_lower
        ON users (LOWER(email));
    """)

    # 7. Fast login lookup: find user by email scoped to their org
    #    Query pattern: WHERE organization_id = ? AND LOWER(email) = LOWER(?)
    op.execute("""
        CREATE UNIQUE INDEX ix_users_org_email
        ON users (organization_id, LOWER(email));
    """)

    # 8. Role-based queries per org: WHERE organization_id = ? AND role = 'admin'
    op.create_index('ix_users_org_role',   'users', ['organization_id', 'role'])

    # 9. Active user filter: WHERE organization_id = ? AND is_active = true
    op.create_index('ix_users_org_active', 'users', ['organization_id', 'is_active'])


def downgrade() -> None:

    # Users — reverse order
    op.drop_index('ix_users_org_active',   table_name='users')
    op.drop_index('ix_users_org_role',     table_name='users')
    op.execute("DROP INDEX IF EXISTS ix_users_org_email;")
    op.execute("DROP INDEX IF EXISTS uq_users_email_lower;")
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'updated_at')

    # Organizations — reverse order
    op.drop_index('ix_organizations_slug_active', table_name='organizations')
    op.drop_index('ix_organizations_slug',        table_name='organizations')
    op.create_unique_constraint('organizations_slug_key', 'organizations', ['slug'])
    op.drop_column('organizations', 'updated_at')