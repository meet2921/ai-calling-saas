# app/api/v1/auth.py
import logging
import time
import secrets
from datetime import timedelta, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
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
from app.schemas.user import UserProfileUpdate
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
from app.core.limiter import limiter

router = APIRouter(tags=["Auth"])
_bearer = HTTPBearer(auto_error=False)
_RESET_PREFIX = "pw:reset:"
logger = logging.getLogger(__name__)


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Attach HttpOnly, Secure, SameSite=Strict cookies to the response."""
    secure = settings.APP_ENV == "production"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Expire both auth cookies immediately."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="Login")
@limiter.limit("10/minute")
async def login(request: Request, response: Response, data: LoginRequest, db: AsyncSession = Depends(get_db)):
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
        logger.warning("Failed login attempt | org: %s | email: %s", data.org_slug, data.email)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive. Contact your admin.")

    # Track last login
    await db.execute(
        update(User).where(User.id == user.id)
        .values(last_login_at=datetime.now(timezone.utc))
    )
    await db.commit()

    access_token  = create_access_token(str(user.id), str(org.id))
    refresh_token = create_refresh_token(str(user.id), str(org.id))
    _set_auth_cookies(response, access_token, refresh_token)

    logger.info("Login success: %s | org: %s | role: %s", user.email, org.slug, user.role)
    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
    }


# ─────────────────────────────────────────────────────────────────────────────
# REFRESH
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse, summary="Refresh token pair")
@limiter.limit("60/minute")
async def refresh(
    request: Request,
    response: Response,
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

    access_token  = create_access_token(user_id, org_id)
    refresh_token = create_refresh_token(user_id, org_id)
    _set_auth_cookies(response, access_token, refresh_token)

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
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
    response: Response,
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
            logger.warning("Logout: invalid token ignored")

    _clear_auth_cookies(response)
    logger.info("Logout: %s", current_user.email)
    return MsgResponse(message="Logged out successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# FORGOT PASSWORD
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/forgot-password", response_model=MsgResponse)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
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

    # Log token to console so devs can test without email (debug level)
    logger.debug(
        "Password reset token for %s | token: %s | link: %s",
        user.email, reset_token, reset_link,
    )

    try:
        await send_password_reset_email(
            to_email=user.email,
            first_name=user.first_name,
            reset_link=reset_link,
            expire_hours=settings.PASSWORD_RESET_EXPIRE_HOURS,
        )
    except Exception:
        logger.exception("Reset email failed for %s (token still valid)", user.email)

    return _ok


# ─────────────────────────────────────────────────────────────────────────────
# RESET PASSWORD
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/reset-password", response_model=MsgResponse)
@limiter.limit("10/minute")
async def reset_password(
    request: Request,
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
        logger.warning("Password reset: token not found or expired")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link is invalid or has expired. Please request a new one.",
        )

    # Delete token immediately (single-use) — prevents race condition
    await redis.delete(redis_key)

    user_id = raw_user_id.decode() if isinstance(raw_user_id, bytes) else raw_user_id
    result  = await db.execute(select(User).where(User.id == user_id))
    user    = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found or account is inactive.",
        )

    user.password_hash = hash_password(data.new_password)
    await db.commit()

    logger.info("Password reset successful for %s", user.email)
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

    logger.info("Password changed for %s", current_user.email)
    return MsgResponse(message="Password changed successfully.")

@router.put("/me", response_model=UserProfile, summary="Update current user profile")
async def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.email:
        existing = (await db.execute(
            select(User)
            .where(User.email == data.email.lower().strip())
            .where(User.id != current_user.id)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use.")
        current_user.email = data.email.lower().strip()

    if data.first_name:
        current_user.first_name = data.first_name

    if data.last_name:
        current_user.last_name = data.last_name


    await db.commit()
    await db.refresh(current_user)

    # 🔹 fetch organization
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