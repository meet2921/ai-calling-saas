"""
Run this ONCE after running migrations to create your Super Admin account.

Usage:
    cd backend
    python create_super_admin.py

Edit the variables below before running.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.models.organization import Organization
from app.models.user import User, UserRole
from app.core.security import hash_password

# ── CONFIGURE THESE ──────────────────────────────────────────────────────────
SUPER_ADMIN_EMAIL      = "superadmin@yourplatform.com"
SUPER_ADMIN_PASSWORD   = "YourStrongPass@123"   # Change this!
SUPER_ADMIN_FIRST_NAME = "Super"
SUPER_ADMIN_LAST_NAME  = "Admin"
PLATFORM_ORG_NAME      = "Platform"
PLATFORM_ORG_SLUG      = "platform-admin"       # Used at login — keep it secret
# ─────────────────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")


async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Check if already exists
        result = await db.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        if result.scalar_one_or_none():
            print(f"✅ Super Admin '{SUPER_ADMIN_EMAIL}' already exists. Nothing to do.")
            return

        # Create platform org
        result = await db.execute(select(Organization).where(Organization.slug == PLATFORM_ORG_SLUG))
        org = result.scalar_one_or_none()

        if not org:
            org = Organization(name=PLATFORM_ORG_NAME, slug=PLATFORM_ORG_SLUG, is_active=True)
            db.add(org)
            await db.flush()
            print(f"✅ Created platform org: '{PLATFORM_ORG_NAME}' (slug={PLATFORM_ORG_SLUG})")

        # Create super admin user
        user = User(
            organization_id=org.id,
            email=SUPER_ADMIN_EMAIL,
            password_hash=hash_password(SUPER_ADMIN_PASSWORD),
            role=UserRole.SUPER_ADMIN,
            first_name=SUPER_ADMIN_FIRST_NAME,
            last_name=SUPER_ADMIN_LAST_NAME,
            is_active=True,
        )
        db.add(user)
        await db.commit()

        print(f"\n{'='*55}")
        print(f"✅ Super Admin created successfully!")
        print(f"   Email    : {SUPER_ADMIN_EMAIL}")
        print(f"   Password : {SUPER_ADMIN_PASSWORD}")
        print(f"   Org Slug : {PLATFORM_ORG_SLUG}")
        print(f"\n   Login at: POST /api/v1/auth/login")
        print(f"   Body: {{")
        print(f'     "org_slug": "{PLATFORM_ORG_SLUG}",')
        print(f'     "email":    "{SUPER_ADMIN_EMAIL}",')
        print(f'     "password": "{SUPER_ADMIN_PASSWORD}"')
        print(f"   }}")
        print(f"{'='*55}\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
