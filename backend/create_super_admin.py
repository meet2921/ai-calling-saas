"""
Run this ONCE after migrations to create your Super Admin account.

    cd backend
    python create_super_admin.py
"""
import asyncio, os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.models.organization import Organization
from app.models.user import User, UserRole
from app.core.security import hash_password

EMAIL      = "superadmin@tierceindia.com"   # ← CHANGE THIS
PASSWORD   = "TierceIndia@123"             # ← CHANGE THIS
FIRST_NAME = "Super"
LAST_NAME  = "Admin"
ORG_SLUG   = "platform-admin"                # ← used at login, keep secret

async def main():
    engine = create_async_engine(os.getenv("DATABASE_URL"), echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        if (await db.execute(select(User).where(User.email == EMAIL))).scalar_one_or_none():
            print(f"Super Admin '{EMAIL}' already exists.")
            return

        org = (await db.execute(select(Organization).where(Organization.slug == ORG_SLUG))).scalar_one_or_none()
        if not org:
            org = Organization(name="Platform", slug=ORG_SLUG, is_active=True)
            db.add(org)
            await db.flush()

        db.add(User(
            organization_id=org.id, email=EMAIL,
            password_hash=hash_password(PASSWORD),
            role=UserRole.SUPER_ADMIN,
            first_name=FIRST_NAME, last_name=LAST_NAME, is_active=True,
        ))
        await db.commit()
        print(f"✅ Super Admin created!")
        print(f"   Login: org_slug={ORG_SLUG}  email={EMAIL}  password={PASSWORD}")

asyncio.run(main())