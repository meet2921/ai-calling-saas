from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
import redis.asyncio as aioredis
from app.models.base import Base

_redis_pool: aioredis.Redis | None = None

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_redis_pool() -> aioredis.Redis:
    """Call this in your FastAPI lifespan / startup event to pre-warm the pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=False,
        )
    return _redis_pool


async def get_redis_client():
    """FastAPI dependency — injects Redis into routes."""
    pool = await get_redis_pool()
    return pool
