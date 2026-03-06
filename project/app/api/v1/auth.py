"""
app/api/v1/auth.py

Public auth endpoints. 
Register has been REMOVED — only Super Admin creates accounts via /api/v1/admin/register.
Users just need to log in with credentials given to them.
"""
import time
import secrets
from datetime import timedelta, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.session import get_db, get_redis_client
from app.models.user import User
from app.models.organization import Organization
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
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
from app.core.email import send_password_reset_email
from app.core.config import settings

router = APIRouter(tags=["Auth"])
_bearer = HTTPBearer(auto_error=False)
_RESET_PREFIX = "pw:reset:"


# ── LOGIN ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="Login with org_slug + email + password")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Credentials are created by the Super Admin. Users only need to log in.
    Body: { "org_slug": "acme-corp", "email": "admin@acme.com", "password": "Pass@123" }
    """
    # 1. Find org by slug (must be active)
    org_result = await db.execute(
        select(Organization)
        .where(Organization.slug == data.org_slug.lower().strip())
        .where(Organization.is_active == True)
        .limit(1)
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 2. Find user scoped to that org
    user_result = await db.execute(
        select(User)
        .where(User.email == data.email.lower().strip())
        .where(User.organization_id == org.id)
    )
    user = user_result.scalar_one_or_none()

    # Same error for wrong email OR wrong password — prevents enumeration
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive. Contact your administrator.")

    # 3. Track last login
    await db.execute(
        update(User).where(User.id == user.id)
        .values(last_login_at=datetime.now(timezone.utc))
    )
    await db.commit()

    print(f"[LOGIN] ✅ {user.email} | org: {org.slug} | role: {user.role}")

    return {
        "access_token":  create_access_token(str(user.id), str(org.id)),
        "refresh_token": create_refresh_token(str(user.id), str(org.id)),
        "token_type":    "bearer",
    }


# ── REFRESH ───────────────────────────────────────────────────────────────────

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

    # Rotate: blacklist old refresh token
    if jti:
        ttl = int(payload.get("exp", 0) - time.time())
        await blacklist_token(redis, jti, max(ttl, 1))

    return {
        "access_token":  create_access_token(user_id, org_id),
        "refresh_token": create_refresh_token(user_id, org_id),
        "token_type":    "bearer",
    }


# ── ME ────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserProfile)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = org_result.scalar_one_or_none()

    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name or "",
        last_name=current_user.last_name or "",
        role=current_user.role.value,
        organization_id=str(current_user.organization_id),
        org_name=org.name if org else "",
        org_slug=org.slug if org else "",
    )


# ── LOGOUT ────────────────────────────────────────────────────────────────────

@router.post("/logout", response_model=MsgResponse)
async def logout(
    data: RefreshRequest | None = None,
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    redis=Depends(get_redis_client),
    current_user: User = Depends(get_current_user),
):
    tokens = []
    if creds:
        tokens.append(creds.credentials)
    if data and data.refresh_token:
        tokens.append(data.refresh_token)

    for raw in tokens:
        try:
            payload = decode_token(raw)
            jti = payload.get("jti")
            if jti:
                ttl = int(payload.get("exp", 0) - time.time())
                await blacklist_token(redis, jti, max(ttl, 1))
        except Exception:
            pass

    print(f"[LOGOUT] ✅ {current_user.email}")
    return MsgResponse(message="Logged out successfully.")


# ── FORGOT PASSWORD ───────────────────────────────────────────────────────────

@router.post("/forgot-password", response_model=MsgResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
):
    """Always returns 200 — never reveals if the email exists (anti-enumeration)."""
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

    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}&org={org.slug}"

    print(f"\n{'='*60}")
    print(f"[RESET] Email : {user.email}")
    print(f"[RESET] Token : {reset_token}")
    print(f"[RESET] Link  : {reset_link}")
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


# ── RESET PASSWORD ────────────────────────────────────────────────────────────

@router.post("/reset-password", response_model=MsgResponse)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
):
    redis_key   = f"{_RESET_PREFIX}{data.reset_token}"
    raw_user_id = await redis.get(redis_key)

    if not raw_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link is invalid or has expired.",
        )

    user_id = raw_user_id.decode() if isinstance(raw_user_id, bytes) else raw_user_id
    result  = await db.execute(select(User).where(User.id == user_id))
    user    = result.scalar_one_or_none()

    if not user or not user.is_active:
        await redis.delete(redis_key)
        raise HTTPException(status_code=400, detail="User not found or inactive.")

    user.password_hash = hash_password(data.new_password)
    await db.commit()
    await redis.delete(redis_key)

    print(f"[RESET] ✅ Password changed for {user.email}")
    return MsgResponse(message="Password reset successfully. Please log in.")


# ── CHANGE PASSWORD (logged in) ───────────────────────────────────────────────

@router.put("/me/password", response_model=MsgResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if data.current_password == data.new_password:
        raise HTTPException(status_code=400, detail="New password must differ from current.")

    current_user.password_hash = hash_password(data.new_password)
    await db.commit()
    return MsgResponse(message="Password changed successfully.")
