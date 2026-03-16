# app/api/v1/auth.py   
import time
import secrets
from datetime import timedelta, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from numpy import exp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db, get_redis_client
from app.models.user import User, UserRole
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


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="Login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login with org_slug + email + password.
    Body: { "org_slug": "abc-xyz", "email": "admin@abc.com", "password": "Secure@123" }
    """
    normalized_email = data.email.lower().strip()

    # Find org by slug
    org_result = await db.execute(
        select(Organization)
        .where(Organization.slug == data.org_slug.lower().strip())
        .where(Organization.is_active == True)
        .limit(1)
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Find user scoped to that org
    user_result = await db.execute(
        select(User)
        .where(User.email == normalized_email)
        .where(User.organization_id == org.id)
    )
    user = user_result.scalar_one_or_none()

    # Same vague error for wrong email AND wrong password → no enumeration
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive. Contact your admin.")

    # Track last login
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


# ─────────────────────────────────────────────────────────────────────────────
# REFRESH
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse, summary="Refresh token pair")
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


# ─────────────────────────────────────────────────────────────────────────────
# ME — requires Authorization: Bearer <access_token>
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user — requires Authorization: Bearer <access_token>",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    HOW TO USE IN SWAGGER:
      1. Login → copy access_token
      2. Click "Authorize 🔒" (top right of Swagger page)
      3. Enter: Bearer <paste_token_here>
      4. Click Authorize → Close → call /me
    """
    org_result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = org_result.scalar_one_or_none()

    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role.value,
        organization_id=str(current_user.organization_id),
        org_name=org.name if org else "",
        org_slug=org.slug if org else "",
    )


# ─────────────────────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/logout", response_model=MsgResponse, summary="Logout — blacklists tokens")
async def logout(
    data: RefreshRequest | None = None,
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    redis=Depends(get_redis_client),
    current_user: User = Depends(get_current_user),
):
    tokens_to_revoke = []
    if creds:
        tokens_to_revoke.append(creds.credentials)
    if data and data.refresh_token:
        tokens_to_revoke.append(data.refresh_token)

    for raw in tokens_to_revoke:
        try:
            payload = decode_token(raw)
            jti = payload.get("jti")
            exp = payload.get("exp")

            if not jti or not exp:
                continue

            ttl = int(exp - time.time())
            await blacklist_token(redis, jti, max(ttl, 1))

        except ValueError:
            print("[LOGOUT] ⚠️ Invalid token ignored")


    print(f"[LOGOUT] ✅ {current_user.email}")
    return MsgResponse(message="Logged out successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# FORGOT PASSWORD
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/forgot-password", response_model=MsgResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
):
    """Always returns 200 — never reveals if email exists (anti-enumeration)."""
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

    # Print token to terminal — use this to test without opening email
    print(f"\n{'='*62}")
    print(f"[RESET] Email  : {user.email}")
    print(f"[RESET] Token  : {reset_token}")
    print(f"[RESET] Link   : {reset_link}")
    print(f"[RESET] → Copy token above. Use in POST /reset-password as 'reset_token'")
    print(f"{'='*62}\n")

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


# ─────────────────────────────────────────────────────────────────────────────
# RESET PASSWORD
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/reset-password", response_model=MsgResponse)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
):
    """
    Body: { "reset_token": "from_terminal_or_email", "new_password": "NewPass1!" }
    Token comes from the [RESET] Token line printed in uvicorn terminal,
    or from the ?token= value in the email link.
    """
    redis_key   = f"{_RESET_PREFIX}{data.reset_token}"
    raw_user_id = await redis.get(redis_key)

    if not raw_user_id:
        print(f"[RESET] ❌ Token not found/expired")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link is invalid or has expired. Please request a new one.",
        )

    user_id = raw_user_id.decode() if isinstance(raw_user_id, bytes) else raw_user_id
    result  = await db.execute(select(User).where(User.id == user_id))
    user    = result.scalar_one_or_none()

    if not user or not user.is_active:
        await redis.delete(redis_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found or account is inactive.",
        )

    user.password_hash = hash_password(data.new_password)
    await db.commit()
    await redis.delete(redis_key)  # single-use

    print(f"[RESET] ✅ Password changed for {user.email}")
    return MsgResponse(message="Password reset successfully. Please log in.")


# ─────────────────────────────────────────────────────────────────────────────
# CHANGE PASSWORD (logged in)
# ─────────────────────────────────────────────────────────────────────────────

@router.put("/me/password", response_model=MsgResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Requires Authorization: Bearer <access_token> header."""
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    if data.current_password == data.new_password:
        raise HTTPException(status_code=400,
            detail="New password must be different from current password.")

    current_user.password_hash = hash_password(data.new_password)
    await db.commit()

    print(f"[AUTH] ✅ Password changed for {current_user.email}")
    return MsgResponse(message="Password changed successfully.")