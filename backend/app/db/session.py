from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import redis.asyncio as aioredis
from app.models.base import Base

_redis_pool: aioredis.Redis | None = None

engine = create_async_engine(settings.DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        # This creates all tables defined in your models
        await conn.run_sync(Base.metadata.create_all)

async def get_redis_pool() -> aioredis.Redis:
    """Call this in your FastAPI lifespan / startup event to pre-warm the pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=False,   # raw bytes — we decode manually where needed
        )
    return _redis_pool


async def get_redis_client():
    """FastAPI dependency — injects Redis into routes."""
    pool = await get_redis_pool()
    return pool
