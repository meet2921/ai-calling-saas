import uuid
import bcrypt
from jose import jwt,  JWTError
from datetime import datetime, timedelta,timezone
from dotenv import load_dotenv
from passlib.context import CryptContext
from app.core.config import settings

# bcrypt for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_BL_PREFIX = "token:blacklist:"   # Redis namespace

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)

# In security.py
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)



def _make_token(user_id: str, org_id: str, token_type: str, expire: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "org_id":  org_id,
        "type":    token_type,
        "jti":     str(uuid.uuid4()),  # unique ID → enables per-token blacklisting
        "iat":     now,
        "exp":     now + expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_access_token(user_id: str, org_id: str) -> str:
    return _make_token(
        user_id, org_id, "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str, org_id: str) -> str:
    return _make_token(
        user_id, org_id, "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
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
# ─── Redis blacklist helpers ──────────────────────────────────────────────────

async def blacklist_token(redis, jti: str, ttl_seconds: int) -> None:
    """Add a token JTI to the Redis blacklist with TTL matching token expiry."""
    await redis.setex(f"{_BL_PREFIX}{jti}", ttl_seconds, "1")


async def is_blacklisted(redis, jti: str) -> bool:
    """Return True if this JTI has been blacklisted (logged out / rotated)."""
    return await redis.exists(f"{_BL_PREFIX}{jti}") == 1
