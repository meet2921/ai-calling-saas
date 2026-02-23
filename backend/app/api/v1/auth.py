from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.schemas.user import UserCreate, UserLogin
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    stmt = select(User).filter(User.email == user_data.email)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 🔹 NEW LOGIC: Handle organization by name
    org_name = user_data.organization_name.strip()

    # Check if organization already exists (case-insensitive)
    org_stmt = select(Organization).filter(
        Organization.name.ilike(org_name)
    )
    org_result = await db.execute(org_stmt)
    org = org_result.scalar_one_or_none()

    # If organization does not exist → create it
    if not org:
        org = Organization(
            name=org_name,
            slug=org_name.lower().replace(" ", "-")
        )
        db.add(org)
        await db.flush()  # Get generated ID without full commit

    # Create new user linked to organization
    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        organization_id=org.id,
        role=UserRole.AGENT  # Keeping your existing role logic
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {"message": "User created successfully"}

@router.post("/login")
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    stmt = select(User).filter(User.email == user_data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({"sub": user.email})

    return {"access_token": token, "token_type": "bearer"}
