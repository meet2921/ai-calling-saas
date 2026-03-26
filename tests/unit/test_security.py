"""
WHITE BOX — app/core/security.py

Tests every internal function: password hashing, JWT creation/decoding,
and Redis blacklist helpers.
"""

import time
import uuid
import pytest
from unittest.mock import AsyncMock

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    blacklist_token,
    is_blacklisted,
)


# ─── Password hashing ─────────────────────────────────────────────────────────

class TestPasswordHashing:

    def test_hash_returns_string(self):
        result = hash_password("Secret@123")
        assert isinstance(result, str)

    def test_hash_is_not_plaintext(self):
        result = hash_password("Secret@123")
        assert result != "Secret@123"

    def test_same_password_produces_different_hashes(self):
        # bcrypt uses random salt — two hashes must differ
        h1 = hash_password("Secret@123")
        h2 = hash_password("Secret@123")
        assert h1 != h2

    def test_verify_correct_password_returns_true(self):
        hashed = hash_password("Correct@123")
        assert verify_password("Correct@123", hashed) is True

    def test_verify_wrong_password_returns_false(self):
        hashed = hash_password("Correct@123")
        assert verify_password("Wrong@123", hashed) is False

    def test_verify_empty_password_returns_false(self):
        hashed = hash_password("Correct@123")
        assert verify_password("", hashed) is False


# ─── JWT token creation ───────────────────────────────────────────────────────

class TestTokenCreation:

    def test_create_access_token_returns_string(self):
        token = create_access_token(str(uuid.uuid4()), str(uuid.uuid4()))
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token_returns_string(self):
        token = create_refresh_token(str(uuid.uuid4()), str(uuid.uuid4()))
        assert isinstance(token, str)

    def test_access_token_has_access_type(self):
        user_id = str(uuid.uuid4())
        org_id  = str(uuid.uuid4())
        token   = create_access_token(user_id, org_id)
        payload = decode_token(token)
        assert payload["type"] == "access"

    def test_refresh_token_has_refresh_type(self):
        user_id = str(uuid.uuid4())
        org_id  = str(uuid.uuid4())
        token   = create_refresh_token(user_id, org_id)
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_token_contains_user_id(self):
        user_id = str(uuid.uuid4())
        token   = create_access_token(user_id, str(uuid.uuid4()))
        payload = decode_token(token)
        assert payload["user_id"] == user_id

    def test_token_contains_org_id(self):
        org_id = str(uuid.uuid4())
        token  = create_access_token(str(uuid.uuid4()), org_id)
        payload = decode_token(token)
        assert payload["org_id"] == org_id

    def test_token_contains_jti(self):
        token   = create_access_token(str(uuid.uuid4()), str(uuid.uuid4()))
        payload = decode_token(token)
        assert "jti" in payload
        assert len(payload["jti"]) > 0

    def test_two_tokens_have_different_jtis(self):
        uid = str(uuid.uuid4())
        oid = str(uuid.uuid4())
        t1  = create_access_token(uid, oid)
        t2  = create_access_token(uid, oid)
        assert decode_token(t1)["jti"] != decode_token(t2)["jti"]


# ─── JWT decoding ─────────────────────────────────────────────────────────────

class TestDecodeToken:

    def test_decode_valid_token(self):
        token   = create_access_token("uid-1", "org-1")
        payload = decode_token(token)
        assert payload["user_id"] == "uid-1"
        assert payload["org_id"]  == "org-1"

    def test_decode_invalid_token_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token("this.is.not.a.jwt")

    def test_decode_tampered_token_raises_value_error(self):
        token   = create_access_token("uid", "org")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(ValueError):
            decode_token(tampered)

    def test_decode_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            decode_token("")


# ─── Redis blacklist ──────────────────────────────────────────────────────────

class TestBlacklist:

    @pytest.mark.asyncio
    async def test_blacklist_token_calls_setex(self):
        redis = AsyncMock()
        redis.setex = AsyncMock()
        jti = str(uuid.uuid4())
        await blacklist_token(redis, jti, ttl_seconds=300)
        redis.setex.assert_called_once()
        call_args = redis.setex.call_args[0]
        assert jti in call_args[0]          # key contains jti
        assert call_args[1] == 300          # ttl is passed correctly

    @pytest.mark.asyncio
    async def test_is_blacklisted_returns_true_when_exists(self):
        redis = AsyncMock()
        redis.exists = AsyncMock(return_value=1)
        result = await is_blacklisted(redis, "some-jti")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_blacklisted_returns_false_when_not_exists(self):
        redis = AsyncMock()
        redis.exists = AsyncMock(return_value=0)
        result = await is_blacklisted(redis, "some-jti")
        assert result is False

    @pytest.mark.asyncio
    async def test_blacklist_uses_correct_key_prefix(self):
        redis = AsyncMock()
        redis.setex = AsyncMock()
        jti = "test-jti-123"
        await blacklist_token(redis, jti, ttl_seconds=60)
        key_used = redis.setex.call_args[0][0]
        assert key_used == f"token:blacklist:{jti}"
