from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db, get_redis_client
from app.core.security import decode_token, is_blacklisted
from app.models.user import User
from app.models.organization import Organization
from app.models.user import UserRole
from sqlalchemy.orm import selectinload
 
# This reads the Bearer token from Authorization header
bearer_scheme = HTTPBearer(auto_error=True)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis_client),
) -> User:
    _unauth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    """
    This dependency runs automatically on protected routes
    1. Reads JWT token from header
    2. Decodes it
    3. Fetches user from database
    4. Returns user to your route

    Usage in route:
    async def my_route(current_user: User = Depends(get_current_user)):
    """
    token = credentials.credentials

    # Decode the token
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # Make sure it is an access token not refresh token
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong token type"
        )
    
     # Step 3: Check blacklist (was it logged out?)
    jti = payload.get("jti")
    if jti and await is_blacklisted(redis, jti):
        print(f"[AUTH] ❌ Token blacklisted (already logged out): {jti}")
        raise _unauth

    # Fetch user from database, including organization to prevent lazy loads
    user_id = payload.get("user_id")
    if not user_id:
        print("[AUTH] ❌ No user_id in token payload")
        raise _unauth
    
    result = await db.execute(
    select(User)
    .options(selectinload(User.organization))
    .where(User.id == user_id)
)
    user = result.scalar_one_or_none()


    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive"
        )
    
    if not user.organization.is_active:
        raise HTTPException(
                status_code=403,
                detail="Organization is suspended"
            )

    return user


async def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Only YOU (super_admin) can call endpoints using this."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin access required.")
    return current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Admin or Super Admin can call endpoints using this."""
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user