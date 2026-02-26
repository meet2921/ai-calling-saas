from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.core.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Registration flow:
    1. Check slug not already taken
    2. Check email not already taken
    3. Create organization
    4. Create owner user
    5. Return tokens
    """

    # Check slug is not taken
    slug_result = await db.execute(
        select(Organization).where(Organization.slug == data.org_slug)
    )
    if slug_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="This organization slug is already taken"
        )

    # Create organization
    org = Organization(
        name=data.org_name,
        slug=data.org_slug,
    )
    db.add(org)
    await db.flush()  # gets org.id without committing yet

    # Check email not taken inside this org
    email_result = await db.execute(
        select(User)
        .where(User.email == data.email)
        .where(User.organization_id == org.id)
    )
    if email_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Create owner user
    user = User(
        organization_id=org.id,
        email=data.email,
        password_hash=hash_password(data.password),  # hash the password
        role=UserRole.OWNER,
        first_name=data.first_name,
        last_name=data.last_name,
    )
    db.add(user)
    await db.commit()        # saves both org and user together
    await db.refresh(user)  # gets final user data back

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
    Login flow:
    1. Find organization by slug
    2. Find user by email in that org
    3. Verify password
    4. Return tokens
    """

    # Find organization
    org_result = await db.execute(
        select(Organization).where(Organization.slug == data.org_slug)
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    # Find user inside that org
    user_result = await db.execute(
        select(User)
        .where(User.email == data.email)
        .where(User.organization_id == org.id)
    )
    user = user_result.scalar_one_or_none()

    # Verify password
    # Note: we return same error for wrong email AND wrong password
    # This prevents attackers from knowing which one is wrong
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Account is inactive"
        )

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
    Refresh flow:
    1. Decode refresh token
    2. Verify it is a refresh token not access token
    3. Issue new access token + new refresh token
    """

    try:
        payload = decode_token(data.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )

    # Make sure this is a refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Wrong token type"
        )

    user_id = payload.get("user_id")
    org_id = payload.get("org_id")

    # Verify user still exists
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="User not found or inactive"
        )

    # Issue new tokens
    new_access_token = create_access_token(user_id, org_id)
    new_refresh_token = create_refresh_token(user_id, org_id)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Protected route example
    Depends(get_current_user) runs automatically:
      → reads token from header
      → decodes it
      → fetches user from database
      → passes user here as current_user
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role,
    }