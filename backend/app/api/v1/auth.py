import time
import secrets
from datetime import timedelta, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db, get_redis_client
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MsgResponse,
    UserProfile,
)

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    blacklist_token,
    is_blacklisted,
)
from app.core.deps import get_current_user
from app.core.email import send_welcome_email, send_password_reset_email
from app.core.config import settings

router = APIRouter(tags=["Auth"])
_bearer = HTTPBearer(auto_error=False)
_RESET_PREFIX = "pw:reset:"


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    normalized_email = data.email.lower().strip()
    normalized_slug = data.org_slug.lower().strip()

    # 1️⃣ Check email already exists
    existing = await db.execute(
        select(User).where(User.email == normalized_email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists. Please log in.",
        )

    # 2️⃣ Check if organization already exists
    result = await db.execute(
        select(Organization).where(Organization.slug == normalized_slug)
    )
    org = result.scalar_one_or_none()

    # 3️⃣ If not exists → create it
    if not org:
        org = Organization(
            name=data.org_name.strip(),
            slug=normalized_slug,
            is_active=True,
        )
        db.add(org)
        await db.flush()  # get org.id without commit

        role = UserRole.ADMIN   # first user becomes admin
    else:
        role = UserRole.USER    # joining existing org → normal user

    # 4️⃣ Create user under that org
    user = User(
        organization_id=org.id,
        email=normalized_email,
        password_hash=hash_password(data.password),
        role=role,
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try again.",
        )

    await db.refresh(user)
    await db.refresh(org)

    access_token  = create_access_token(str(user.id), str(org.id))
    refresh_token = create_refresh_token(str(user.id), str(org.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    normalized_email = data.email.lower().strip()

    org_result = await db.execute(
        select(Organization)
        .where(Organization.slug == data.org_slug.lower().strip())
        .where(Organization.is_active == True)
        .limit(1)
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_result = await db.execute(
        select(User)
        .where(User.email == normalized_email)
        .where(User.organization_id == org.id)
    )
    user = user_result.scalar_one_or_none()

    # Look for something like this in auth.py:
    # if not user:
    #     print("DEBUG: Auth failed - either user not found or password wrong") # Add this
    #     raise HTTPException(status_code=401, detail="Incorrect email or password")


    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")
        # return None

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(last_login_at=datetime.now(timezone.utc))
    )
    await db.commit()

    access_token  = create_access_token(str(user.id), str(org.id))
    refresh_token = create_refresh_token(str(user.id), str(org.id))

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
):
    try:
        payload = decode_token(data.refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Wrong token type")

    jti = payload.get("jti")
    if jti and await is_blacklisted(redis, jti):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    user_id = payload.get("user_id")
    org_id  = payload.get("org_id")

    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    if jti:
        ttl = int(payload.get("exp", 0) - time.time())
        await blacklist_token(redis, jti, max(ttl, 1))

    return {
        "access_token":  create_access_token(user_id, org_id),
        "refresh_token": create_refresh_token(user_id, org_id),
        "token_type":    "bearer",
    }


# @router.get("/me")
# async def get_me(current_user: User = Depends(get_current_user)):
#     return {
#         "id":              str(current_user.id),
#         "email":           current_user.email,
#         "first_name":      current_user.first_name,
#         "last_name":       current_user.last_name,
#         "role":            current_user.role,
#         "organization_id": str(current_user.organization_id),
#     }

@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=str(current_user.role),
        organization_id=str(current_user.organization_id),
    )


@router.post("/logout", response_model=MsgResponse)
async def logout(
    data: RefreshRequest | None = None,
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    redis=Depends(get_redis_client),
    current_user: User = Depends(get_current_user),
):
    """
    Send:
      Header: Authorization: Bearer <access_token>
      Body (optional): { "refresh_token": "..." }

    Blacklists both tokens immediately.
    """
    tokens_to_revoke = []
    if creds:
        tokens_to_revoke.append(creds.credentials)
    if data and data.refresh_token:
        tokens_to_revoke.append(data.refresh_token)

    for raw in tokens_to_revoke:
        try:
            payload = decode_token(raw)
            jti = payload.get("jti")
            if jti:
                ttl = int(payload.get("exp", 0) - time.time())
                await blacklist_token(redis, jti, max(ttl, 1))
        except Exception:
            pass

    print(f"[LOGOUT] ✅ {current_user.email} logged out")
    return MsgResponse(message="Logged out successfully.")


@router.post("/forgot-password", response_model=MsgResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
):
    """
    Sends reset email. Always returns 200 (no user enumeration).

    After calling this, look in the UVICORN TERMINAL for:
      [RESET] Token → xxxxxxxx

    Use that token value in POST /reset-password as "reset_token".
    """
    _ok = MsgResponse(message="If that email is registered, a reset link has been sent.")

    org_result = await db.execute(
        select(Organization)
        .where(Organization.slug == data.org_slug.lower().strip())
        .where(Organization.is_active == True)
        .limit(1)
    )
    org = org_result.scalar_one_or_none()
    if not org:
        return _ok

    user_result = await db.execute(
        select(User)
        .where(User.email == data.email.lower().strip())
        .where(User.organization_id == org.id)
    )
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        return _ok

    reset_token = secrets.token_urlsafe(32)
    redis_key   = f"{_RESET_PREFIX}{reset_token}"
    ttl         = int(timedelta(hours=settings.PASSWORD_RESET_EXPIRE_HOURS).total_seconds())
    await redis.setex(redis_key, ttl, str(user.id))

    reset_link = (
        f"{settings.FRONTEND_URL}/reset-password"
        f"?token={reset_token}&org={org.slug}"
    )

    # ── ALWAYS print to terminal so you can test without opening email ────────
    print(f"\n{'='*60}")
    print(f"[RESET] Password reset requested for: {user.email}")
    print(f"[RESET] Token  → {reset_token}")
    print(f"[RESET] Link   → {reset_link}")
    print(f"[RESET] Use token above in POST /reset-password as 'reset_token'")
    print(f"{'='*60}\n")

    try:
        await send_password_reset_email(
            to_email=user.email,
            first_name=user.first_name,
            reset_link=reset_link,
            expire_hours=settings.PASSWORD_RESET_EXPIRE_HOURS,
        )
    except Exception as e:
        print(f"[EMAIL] ⚠️  Reset email failed (token above still works): {e}")

    return _ok

@router.post("/reset-password", response_model=MsgResponse)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
):
    """
    FIX FOR 422 — send this exact JSON body:

      {
        "reset_token": "paste_the_token_here",
        "new_password": "YourNewPass1!"
      }

    The token comes from:
      - The uvicorn terminal: [RESET] Token → xxxxxxxx
      - OR the email link:    ?token=xxxxxxxx  (copy just this part)

    Password rules: 8+ chars, uppercase, lowercase, number, special char.
    Examples: MyPass1!   Secure@123   Hello#2024
    """
    redis_key   = f"{_RESET_PREFIX}{data.reset_token}"
    raw_user_id = await redis.get(redis_key)

    if not raw_user_id:
        print(f"[RESET] ❌ Token not found in Redis: {data.reset_token[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link is invalid or has expired. Please request a new one.",
        )

    user_id = raw_user_id.decode() if isinstance(raw_user_id, bytes) else raw_user_id

    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()

    if not user or not user.is_active:
        await redis.delete(redis_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found or account is inactive.",
        )

    user.password_hash = hash_password(data.new_password)
    await db.commit()
    await redis.delete(redis_key)   # single-use: delete after success

    print(f"[RESET] ✅ Password reset successfully for {user.email}")
    return MsgResponse(message="Password reset successfully. Please log in.")