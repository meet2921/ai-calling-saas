import bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

security = HTTPBearer()

SECRET_KEY = "0d7946e968bd8638db5ba5ec62955513d64e877be4160bebe9646ea3d8c4cdcc"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password[:72].encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password[:72].encode(), hashed_password.encode())

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        subject = payload.get("sub")
        if not subject:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Fetch user from database
    from app.models.user import User
    from uuid import UUID as PyUUID
    
    # Try to find by email first, then by user ID
    stmt = select(User).filter(User.email == subject)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    # If not found by email, try by ID
    if not user:
        try:
            user_id = PyUUID(subject)
            stmt = select(User).filter(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
        except (ValueError, TypeError):
            pass
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user