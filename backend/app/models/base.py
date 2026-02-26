from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import (create_async_engine,async_sessionmaker,AsyncSession)
from app.core.config import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # checks connection is alive before using it
    echo=settings.DEBUG, # logs SQL queries when DEBUG=true
)

# Session factory — creates a new session for each request
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass
