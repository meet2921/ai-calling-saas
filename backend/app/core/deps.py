from typing import Optional
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db, get_redis_client
from app.core.security import decode_token, is_blacklisted
from app.models.user import User, UserRole

# auto_error=False so we can fall back to the HttpOnly cookie
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    access_token: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
) -> User:
    """
    Reads the JWT from Authorization: Bearer header first,
    then falls back to the HttpOnly access_token cookie set by the server.
    """
    _unauth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials:
        token = credentials.credentials
    elif access_token:
        token = access_token
    else:
        raise _unauth

    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong token type",
        )

    jti = payload.get("jti")
    if jti and await is_blacklisted(redis, jti):
        raise _unauth

    user_id = payload.get("user_id")
    if not user_id:
        raise _unauth

    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive")

    if not user.organization or not user.organization.is_active:
        raise HTTPException(status_code=403, detail="Organization is suspended")

    return user


async def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Only super_admin can call endpoints using this."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin access required.")
    return current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Admin or Super Admin can call endpoints using this."""
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user
