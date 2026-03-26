"""
BLACK BOX — /api/v1/wallet/*

Tests wallet balance, transaction history, and summary endpoints.
Verifies response shape, correct calculation of estimated cost remaining,
and graceful handling of org with no wallet.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from tests.conftest import ORG_ID, WALLET_ID


def _make_wallet(minutes=100, rate=0.50):
    w = MagicMock()
    w.id                      = WALLET_ID
    w.organization_id         = ORG_ID
    w.minutes_balance         = minutes
    w.rate_per_minute         = rate
    w.total_minutes_purchased = 200
    w.total_minutes_used      = 100
    w.total_amount_paid       = 100.0
    return w


def _make_transaction(tx_type="credit", minutes=100, amount=50.0):
    tx = MagicMock()
    tx.id               = uuid.uuid4()
    tx.transaction_type = tx_type
    tx.minutes          = minutes
    tx.amount_inr       = amount
    tx.rate_per_minute  = 0.50
    tx.balance_after    = 100
    tx.description      = "Test transaction"
    tx.call_log_id      = None
    tx.created_at       = MagicMock(__str__=lambda self: "2024-01-01T00:00:00")
    return tx


# ─── GET /wallet/balance ──────────────────────────────────────────────────────

class TestGetWalletBalance:

    @pytest.mark.asyncio
    async def test_returns_balance_fields(self, auth_client, mock_db):
        wallet = _make_wallet(minutes=50, rate=1.0)
        mock_db.execute.return_value.scalar_one_or_none.return_value = wallet

        resp = await auth_client.get("/api/v1/wallet/balance")

        assert resp.status_code == 200
        body = resp.json()
        assert body["minutes_balance"]         == 50
        assert body["rate_per_minute"]         == 1.0
        assert body["total_minutes_purchased"] == 200
        assert body["total_minutes_used"]      == 100
        assert body["total_amount_paid"]       == 100.0

    @pytest.mark.asyncio
    async def test_creates_wallet_if_not_exists(self, auth_client, mock_db):
        """When no wallet exists, get_or_create_wallet creates one with 0 balance."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        resp = await auth_client.get("/api/v1/wallet/balance")

        assert resp.status_code == 200
        assert resp.json()["minutes_balance"] == 0

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_403(self, client):
        resp = await client.get("/api/v1/wallet/balance")
        assert resp.status_code in (401, 403)


# ─── GET /wallet/transactions ─────────────────────────────────────────────────

class TestGetWalletTransactions:

    @pytest.mark.asyncio
    async def test_returns_transaction_list(self, auth_client, mock_db):
        wallet = _make_wallet()
        txs = [_make_transaction("credit", 100, 50.0), _make_transaction("debit", 2, 0.0)]
        mock_db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": wallet}),
            MagicMock(**{"scalars.return_value.all.return_value": txs}),
        ]

        resp = await auth_client.get("/api/v1/wallet/transactions")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"]            == 2
        assert len(body["transactions"]) == 2

    @pytest.mark.asyncio
    async def test_transaction_has_required_fields(self, auth_client, mock_db):
        wallet = _make_wallet()
        tx = _make_transaction()
        mock_db.execute.side_effect = [
            MagicMock(**{"scalar_one_or_none.return_value": wallet}),
            MagicMock(**{"scalars.return_value.all.return_value": [tx]}),
        ]

        resp = await auth_client.get("/api/v1/wallet/transactions")

        assert resp.status_code == 200
        tx_body = resp.json()["transactions"][0]
        assert "id"             in tx_body
        assert "type"           in tx_body
        assert "minutes"        in tx_body
        assert "amount_inr"     in tx_body
        assert "balance_after"  in tx_body
        assert "created_at"     in tx_body

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_wallet(self, auth_client, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        resp = await auth_client.get("/api/v1/wallet/transactions")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"]        == 0
        assert body["transactions"] == []


# ─── GET /wallet/summary ──────────────────────────────────────────────────────

class TestGetWalletSummary:

    @pytest.mark.asyncio
    async def test_returns_summary_fields(self, auth_client, mock_db):
        wallet = _make_wallet(minutes=80, rate=2.0)
        mock_db.execute.return_value.scalar_one_or_none.return_value = wallet

        resp = await auth_client.get("/api/v1/wallet/summary")

        assert resp.status_code == 200
        body = resp.json()
        assert "minutes_balance"         in body
        assert "rate_per_minute"         in body
        assert "total_minutes_purchased" in body
        assert "total_minutes_used"      in body
        assert "total_amount_paid"       in body
        assert "estimated_cost_remaining" in body

    @pytest.mark.asyncio
    async def test_estimated_cost_is_correct(self, auth_client, mock_db):
        # 80 minutes × ₹2.0/min = ₹160.0
        wallet = _make_wallet(minutes=80, rate=2.0)
        mock_db.execute.return_value.scalar_one_or_none.return_value = wallet

        resp = await auth_client.get("/api/v1/wallet/summary")

        assert resp.json()["estimated_cost_remaining"] == 160.0

    @pytest.mark.asyncio
    async def test_returns_zeros_when_no_wallet(self, auth_client, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        resp = await auth_client.get("/api/v1/wallet/summary")

        assert resp.status_code == 200
        body = resp.json()
        assert body["minutes_balance"]            == 0
        assert body["estimated_cost_remaining"]   == 0
