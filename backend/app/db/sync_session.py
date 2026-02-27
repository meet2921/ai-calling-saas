from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Convert async URL → sync URL for Celery
DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql+asyncpg",
    "postgresql"
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)