"""
BLACK BOX — POST /api/v1/auth/*

Tests the auth API surface from the outside: correct HTTP status codes,
response shapes, and security behaviour (wrong creds, inactive users,
token blacklisting, password rules).
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.security import hash_password, create_refresh_token
from app.models.user import UserRole
from tests.conftest import ORG_ID, USER_ID


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_org(is_active=True):
    org = MagicMock()
    org.id        = ORG_ID
    org.slug      = "test-corp"
    org.is_active = is_active
    return org


def _make_user(is_active=True, password="Admin@123"):
    user = MagicMock()
    user.id              = USER_ID
    user.organization_id = ORG_ID
    user.email           = "admin@test.com"
    user.first_name      = "Test"
    user.last_name       = "Admin"
    user.role            = UserRole.ADMIN
    user.is_active       = is_active
    user.password_hash   = hash_password(password)
    user.organization    = _make_org(is_active)
    return user


# ─── POST /login ──────────────────────────────────────────────────────────────

class TestLogin:

    @pytest.mark.asyncio
    async def test_valid_credentials_return_tokens(self, client, mock_db):
        org  = _make_org()
        user = _make_user()
        mock_db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": org}),   # org lookup
            MagicMock(**{"scalar_one_or_none.return_value": user}),  # user lookup
            MagicMock(),                                              # update last_login_at
        ]

        resp = await client.post("/api/v1/auth/login", json={
            "org_slug": "test-corp",
            "email":    "admin@test.com",
            "password": "Admin@123",
        })

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token"  in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_wrong_password_returns_401(self, client, mock_db):
        org  = _make_org()
        user = _make_user(password="Admin@123")
        mock_db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": org}),
            MagicMock(**{"scalar_one_or_none.return_value": user}),
        ]

        resp = await client.post("/api/v1/auth/login", json={
            "org_slug": "test-corp",
            "email":    "admin@test.com",
            "password": "WrongPass@1",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_org_slug_returns_401(self, client, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        resp = await client.post("/api/v1/auth/login", json={
            "org_slug": "no-such-org",
            "email":    "admin@test.com",
            "password": "Admin@123",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_inactive_user_returns_401(self, client, mock_db):
        org  = _make_org()
        user = _make_user(is_active=False)
        mock_db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": org}),
            MagicMock(**{"scalar_one_or_none.return_value": user}),
        ]

        resp = await client.post("/api/v1/auth/login", json={
            "org_slug": "test-corp",
            "email":    "admin@test.com",
            "password": "Admin@123",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_fields_returns_422(self, client):
        resp = await client.post("/api/v1/auth/login", json={"email": "x@x.com"})
        assert resp.status_code == 422


# ─── POST /refresh ────────────────────────────────────────────────────────────

class TestRefresh:

    @pytest.mark.asyncio
    async def test_valid_refresh_token_returns_new_tokens(self, client, mock_db, mock_redis):
        user = _make_user()
        refresh_token = create_refresh_token(str(USER_ID), str(ORG_ID))

        mock_db.execute.return_value.scalar_one_or_none.return_value = user
        mock_redis.exists = AsyncMock(return_value=0)   # not blacklisted

        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, client):
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not.a.token"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_blacklisted_token_returns_401(self, client, mock_db, mock_redis):
        refresh_token = create_refresh_token(str(USER_ID), str(ORG_ID))
        mock_redis.exists = AsyncMock(return_value=1)   # blacklisted

        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 401


# ─── GET /me ──────────────────────────────────────────────────────────────────

class TestGetMe:

    @pytest.mark.asyncio
    async def test_returns_user_profile(self, auth_client, mock_db, test_user, test_org):
        mock_db.execute.return_value.scalar_one_or_none.return_value = test_org

        resp = await auth_client.get("/api/v1/auth/me")

        assert resp.status_code == 200
        body = resp.json()
        assert body["email"]      == test_user.email
        assert body["first_name"] == test_user.first_name
        assert "role"             in body

    @pytest.mark.asyncio
    async def test_no_token_returns_403(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)


# ─── POST /logout ─────────────────────────────────────────────────────────────

class TestLogout:

    @pytest.mark.asyncio
    async def test_logout_returns_success_message(self, auth_client, mock_db, test_user, test_org):
        user = _make_user()
        mock_db.execute.return_value.scalar_one_or_none.return_value = user
        refresh_token = create_refresh_token(str(USER_ID), str(ORG_ID))

        resp = await auth_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        assert "logged out" in resp.json()["message"].lower()


# ─── POST /forgot-password ────────────────────────────────────────────────────

class TestForgotPassword:

    @pytest.mark.asyncio
    async def test_always_returns_200(self, client, mock_db):
        """Anti-enumeration: returns 200 whether or not email exists."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        resp = await client.post("/api/v1/auth/forgot-password", json={
            "org_slug": "test-corp",
            "email":    "nobody@test.com",
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_generic_message(self, client, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        resp = await client.post("/api/v1/auth/forgot-password", json={
            "org_slug": "test-corp",
            "email":    "nobody@test.com",
        })
        assert "sent" in resp.json()["message"].lower()


# ─── POST /reset-password ─────────────────────────────────────────────────────

class TestResetPassword:

    @pytest.mark.asyncio
    async def test_invalid_token_returns_400(self, client, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)   # token not in Redis

        resp = await client.post("/api/v1/auth/reset-password", json={
            "reset_token":  "bad-token",
            "new_password": "NewPass@123",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_token_resets_password(self, client, mock_db, mock_redis):
        user = _make_user()
        mock_redis.get    = AsyncMock(return_value=str(USER_ID).encode())
        mock_redis.delete = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = user

        resp = await client.post("/api/v1/auth/reset-password", json={
            "reset_token":  "valid-reset-token",
            "new_password": "NewPass@123",
        })
        assert resp.status_code == 200
        assert "reset" in resp.json()["message"].lower()


# ─── PUT /me/password ─────────────────────────────────────────────────────────

class TestChangePassword:

    @pytest.mark.asyncio
    async def test_wrong_current_password_returns_400(self, auth_client):
        resp = await auth_client.put("/api/v1/auth/me/password", json={
            "current_password": "WrongPass@1",
            "new_password":     "NewPass@123",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_same_password_returns_400(self, auth_client):
        resp = await auth_client.put("/api/v1/auth/me/password", json={
            "current_password": "Admin@123",
            "new_password":     "Admin@123",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_password_change_returns_200(self, auth_client):
        resp = await auth_client.put("/api/v1/auth/me/password", json={
            "current_password": "Admin@123",
            "new_password":     "NewPass@123",
        })
        assert resp.status_code == 200
