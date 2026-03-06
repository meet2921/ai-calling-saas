"""Update userrole enum: remove agent/owner, add super_admin

Revision ID: update_user_roles_001
Revises: f673082faa2b
Create Date: 2025-03-06
"""
from alembic import op
import sqlalchemy as sa

revision = 'update_user_roles_001'
down_revision = 'f673082faa2b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add a temp column with text type
    op.add_column('users', sa.Column('role_temp', sa.String(50), nullable=True))

    # 2. Copy current role values to temp
    op.execute("UPDATE users SET role_temp = role::text")

    # 3. Drop old column and enum
    op.drop_column('users', 'role')
    op.execute("DROP TYPE IF EXISTS userrole CASCADE")

    # 4. Create new enum with correct values
    op.execute("CREATE TYPE userrole AS ENUM ('super_admin', 'admin')")

    # 5. Add new role column
    op.add_column('users', sa.Column(
        'role',
        sa.Enum('super_admin', 'admin', name='userrole'),
        nullable=False,
        server_default='admin'
    ))

    # 6. Map old values → new values
    op.execute("""
        UPDATE users SET role = CASE
            WHEN role_temp IN ('owner', 'admin') THEN 'admin'::userrole
            WHEN role_temp = 'agent'             THEN 'admin'::userrole
            ELSE 'admin'::userrole
        END
    """)

    # Note: Manually set your own account to super_admin after migration:
    # UPDATE users SET role = 'super_admin' WHERE email = 'your@email.com';

    # 7. Drop temp column
    op.drop_column('users', 'role_temp')

    # 8. Add unique constraint to email if not exists
    op.create_unique_constraint('uq_users_email', 'users', ['email'])


def downgrade() -> None:
    op.execute("ALTER TYPE userrole RENAME TO userrole_new")
    op.execute("CREATE TYPE userrole AS ENUM ('agent', 'owner', 'admin')")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING 'admin'::userrole")
    op.execute("DROP TYPE userrole_new")
    op.drop_constraint('uq_users_email', 'users', type_='unique')
