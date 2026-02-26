import bcrypt
<<<<<<< HEAD
from jose import jwt,  JWTError
from datetime import datetime, timedelta
from dotenv import load_dotenv
from passlib.context import CryptContext
from app.core.config import settings

# bcrypt for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
=======
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
>>>>>>> 936b9b8af513963bd848e80ad5be29b9737abcf2

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

<<<<<<< HEAD
def create_access_token(user_id: str, org_id: str) -> str:
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "user_id": user_id,
        "org_id": org_id,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

def create_refresh_token(user_id: str, org_id: str) -> str:
    expire = datetime.utcnow() + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "user_id": user_id,
        "org_id": org_id,
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise ValueError("Invalid or expired token")
=======
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
>>>>>>> 936b9b8af513963bd848e80ad5be29b9737abcf2
