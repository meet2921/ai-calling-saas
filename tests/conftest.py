"""
Shared fixtures for all tests.

Strategy:
- Unit tests  : test pure functions directly; mock AsyncSession for services
- Integration : override FastAPI dependencies (get_db, get_redis_client,
                get_current_user) so tests never touch a real database or Redis
"""

# ── Set required env vars BEFORE any app imports ──────────────────────────────
# pydantic-settings reads from os.environ first, then .env file.
# Since tests run from the project root (not backend/), the backend/.env is
# not on the search path. We inject dummy values here so Settings() never fails.
import os
os.environ.setdefault("DATABASE_URL",      "postgresql+asyncpg://test:test@localhost/test_db")
os.environ.setdefault("SYNC_DATABASE_URL", "postgresql://test:test@localhost/test_db")
os.environ.setdefault("REDIS_URL",         "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY",        "test-secret-key-for-testing-only-32chars!")
os.environ.setdefault("BOLNA_API_KEY",     "test-bolna-key")
os.environ.setdefault("BOLNA_API_URL",     "https://api.bolna.ai/v2")
os.environ.setdefault("BOLNA_WEBHOOK_SECRET", "")
# ──────────────────────────────────────────────────────────────────────────────

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import get_db, get_redis_client
from app.core.deps import get_current_user
from app.core.security import hash_password, create_access_token
from app.models.user import UserRole


# ─── Reusable IDs ─────────────────────────────────────────────────────────────

ORG_ID   = uuid.uuid4()
USER_ID  = uuid.uuid4()
CAMP_ID  = uuid.uuid4()
LEAD_ID  = uuid.uuid4()
WALLET_ID = uuid.uuid4()


# ─── Mock Redis ───────────────────────────────────────────────────────────────

@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.exists  = AsyncMock(return_value=0)       # token not blacklisted
    redis.setex   = AsyncMock(return_value=True)
    redis.get     = AsyncMock(return_value=None)
    redis.delete  = AsyncMock(return_value=1)
    return redis


# ─── Mock DB helpers ──────────────────────────────────────────────────────────

def make_scalar_result(value):
    """Return a mock execute() result where .scalar_one_or_none() → value."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar.return_value = value
    r.scalars.return_value.all.return_value = value if isinstance(value, list) else ([] if value is None else [value])
    r.fetchone.return_value = (value,) if value else None
    return r


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.add       = MagicMock()
    session.add_all   = MagicMock()
    session.commit    = AsyncMock()
    session.refresh   = AsyncMock()
    session.rollback  = AsyncMock()
    session.delete    = AsyncMock()
    session.flush     = AsyncMock()
    session.get       = AsyncMock(return_value=None)
    session.execute   = AsyncMock(return_value=make_scalar_result(None))
    session.scalar    = AsyncMock(return_value=0)
    return session


# ─── Domain objects (plain MagicMock, no DB needed) ──────────────────────────

@pytest.fixture
def test_org():
    org = MagicMock()
    org.id        = ORG_ID
    org.name      = "Test Corp"
    org.slug      = "test-corp"
    org.is_active = True
    return org


@pytest.fixture
def test_user(test_org):
    user = MagicMock()
    user.id              = USER_ID
    user.organization_id = ORG_ID
    user.email           = "admin@test.com"
    user.first_name      = "Test"
    user.last_name       = "Admin"
    user.role            = UserRole.ADMIN
    user.is_active       = True
    user.password_hash   = hash_password("Admin@123")
    user.organization    = test_org
    return user


@pytest.fixture
def test_campaign():
    from app.models.campaigns import CampaignStatus
    c = MagicMock()
    c.id              = CAMP_ID
    c.name            = "Test Campaign"
    c.description     = "A test campaign"
    c.organization_id = ORG_ID
    c.bolna_agent_id  = "agent-abc-123"
    c.status          = CampaignStatus.draft
    c.is_processing   = False
    return c


@pytest.fixture
def test_wallet():
    w = MagicMock()
    w.id                      = WALLET_ID
    w.organization_id         = ORG_ID
    w.minutes_balance         = 100
    w.rate_per_minute         = 0.50
    w.total_minutes_purchased = 200
    w.total_minutes_used      = 100
    w.total_amount_paid       = 100.0
    return w


# ─── Auth helpers ─────────────────────────────────────────────────────────────

@pytest.fixture
def auth_token():
    return create_access_token(str(USER_ID), str(ORG_ID))


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ─── HTTP clients ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(mock_db, mock_redis):
    """Unauthenticated test client — DB and Redis are mocked."""
    async def _db():
        yield mock_db

    app.dependency_overrides[get_db]           = _db
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(mock_db, mock_redis, test_user):
    """Authenticated test client — get_current_user returns test_user directly."""
    async def _db():
        yield mock_db

    app.dependency_overrides[get_db]             = _db
    app.dependency_overrides[get_redis_client]   = lambda: mock_redis
    app.dependency_overrides[get_current_user]   = lambda: test_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
