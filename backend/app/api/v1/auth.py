from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.core.deps import get_current_user

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    1. Check if org slug already exists
    2. If not → create organization automatically
    3. Create owner user inside that org
    4. Return tokens
    No separate org creation API needed
    """

    # Check slug not taken
    slug_check = await db.execute(
        select(Organization).where(Organization.slug == data.org_slug)
    )
    if slug_check.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Organization slug already taken. Choose another."
        )

    # Create organization automatically
    org = Organization(
        name=data.org_name,
        slug=data.org_slug,
    )
    db.add(org)
    await db.flush()  # gets org.id without committing yet

    # Check email not already used in this org
    email_check = await db.execute(
        select(User)
        .where(User.email == data.email)
    )
    if email_check.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Email already registered in this organization"
        )

    # Create owner user
    user = User(
        organization_id=org.id,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.OWNER,
        first_name=data.first_name,
        last_name=data.last_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create tokens
    access_token = create_access_token(str(user.id), str(org.id))
    refresh_token = create_refresh_token(str(user.id), str(org.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    1. Find org by slug
    2. Find user by email inside that org
    3. Verify password
    4. Return tokens
    """

    # Find org
    org_result = await db.execute(
        select(Organization).where(Organization.slug == data.org_slug)
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Find user inside org
    user_result = await db.execute(
        select(User)
        .where(User.email == data.email)
        .where(User.organization_id == org.id)
    )
    user = user_result.scalar_one_or_none()

    # Verify password
    # Same error for wrong email AND wrong password
    # Prevents attacker knowing which one is wrong
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")

    # Create tokens
    access_token = create_access_token(str(user.id), str(org.id))
    refresh_token = create_refresh_token(str(user.id), str(org.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    1. Decode refresh token
    2. Verify it is refresh type
    3. Return new tokens
    """
    try:
        payload = decode_token(data.refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Wrong token type")

    user_id = payload.get("user_id")
    org_id = payload.get("org_id")

    # Verify user still exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return {
        "access_token": create_access_token(user_id, org_id),
        "refresh_token": create_refresh_token(user_id, org_id),
        "token_type": "bearer"
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Protected route
    Requires valid access_token in header
    Authorization: Bearer <access_token>
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role,
        "organization_id": str(current_user.organization_id)
    }