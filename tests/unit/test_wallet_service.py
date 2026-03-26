"""
WHITE BOX — app/services/wallet_service.py

Tests internal logic: minute calculations, credit/debit math,
balance floor (never go below 0), transaction creation, edge cases.

Mock pattern: db.execute must return a plain MagicMock (not AsyncMock),
otherwise .scalar_one_or_none() returns an unawaited coroutine.
"""

import math
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.wallet_service import (
    credit_wallet,
    deduct_minutes_for_call,
    get_balance,
    has_sufficient_balance,
    get_or_create_wallet,
)
from app.models.wallet import TransactionType


def _mock_wallet(minutes=100, rate=0.50):
    w = MagicMock()
    w.id                      = uuid.uuid4()
    w.organization_id         = uuid.uuid4()
    w.minutes_balance         = minutes
    w.rate_per_minute         = rate
    w.total_minutes_purchased = minutes
    w.total_minutes_used      = 0
    w.total_amount_paid       = 0.0
    return w


def _db_returning(wallet):
    """Create an AsyncMock db whose execute() returns a plain MagicMock result."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = wallet
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    db.add     = MagicMock()
    db.flush   = AsyncMock()
    db.commit  = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ─── get_or_create_wallet ─────────────────────────────────────────────────────

class TestGetOrCreateWallet:

    @pytest.mark.asyncio
    async def test_returns_existing_wallet(self):
        wallet = _mock_wallet()
        db = _db_returning(wallet)
        result = await get_or_create_wallet(str(uuid.uuid4()), db)
        assert result is wallet

    @pytest.mark.asyncio
    async def test_creates_wallet_when_not_found(self):
        db = _db_returning(None)
        result = await get_or_create_wallet(str(uuid.uuid4()), db)
        db.add.assert_called_once()
        assert result.minutes_balance == 0


# ─── credit_wallet ────────────────────────────────────────────────────────────

class TestCreditWallet:

    @pytest.mark.asyncio
    async def test_adds_correct_minutes(self):
        wallet = _mock_wallet(minutes=0, rate=1.0)
        db = _db_returning(wallet)

        result = await credit_wallet(
            organization_id=str(uuid.uuid4()),
            amount_inr=100.0,
            rate_per_minute=1.0,
            description="Top-up",
            db=db,
        )
        assert result["minutes_added"] == 100
        assert result["new_balance"]   == 100

    @pytest.mark.asyncio
    async def test_floors_minutes_calculation(self):
        wallet = _mock_wallet(minutes=0, rate=3.0)
        db = _db_returning(wallet)

        result = await credit_wallet(
            organization_id=str(uuid.uuid4()),
            amount_inr=10.0,
            rate_per_minute=3.0,
            description="Small top-up",
            db=db,
        )
        assert result["minutes_added"] == math.floor(10.0 / 3.0)

    @pytest.mark.asyncio
    async def test_raises_when_amount_too_small(self):
        wallet = _mock_wallet(minutes=0, rate=10.0)
        db = _db_returning(wallet)

        with pytest.raises(ValueError, match="too small"):
            await credit_wallet(
                organization_id=str(uuid.uuid4()),
                amount_inr=5.0,
                rate_per_minute=10.0,
                description="Bad top-up",
                db=db,
            )

    @pytest.mark.asyncio
    async def test_creates_credit_transaction(self):
        wallet = _mock_wallet(minutes=0, rate=1.0)
        db = _db_returning(wallet)

        await credit_wallet(
            organization_id=str(uuid.uuid4()),
            amount_inr=50.0,
            rate_per_minute=1.0,
            description="Credit",
            db=db,
        )
        db.add.assert_called_once()
        tx = db.add.call_args[0][0]
        assert tx.transaction_type == TransactionType.CREDIT
        assert tx.minutes == 50

    @pytest.mark.asyncio
    async def test_updates_total_amount_paid(self):
        wallet = _mock_wallet(minutes=0, rate=1.0)
        wallet.total_amount_paid = 0.0
        db = _db_returning(wallet)

        await credit_wallet(
            organization_id=str(uuid.uuid4()),
            amount_inr=200.0,
            rate_per_minute=1.0,
            description="Big top-up",
            db=db,
        )
        assert wallet.total_amount_paid == 200.0


# ─── deduct_minutes_for_call ──────────────────────────────────────────────────

class TestDeductMinutesForCall:

    @pytest.mark.asyncio
    async def test_deducts_correct_minutes_ceiling(self):
        wallet = _mock_wallet(minutes=10)
        db = _db_returning(wallet)

        result = await deduct_minutes_for_call(
            organization_id=str(uuid.uuid4()),
            duration_seconds=65,
            call_log_id=str(uuid.uuid4()),
            db=db,
        )
        assert result["minutes_deducted"] == 2
        assert wallet.minutes_balance     == 8

    @pytest.mark.asyncio
    async def test_exactly_one_minute_call(self):
        wallet = _mock_wallet(minutes=10)
        db = _db_returning(wallet)

        result = await deduct_minutes_for_call(
            organization_id=str(uuid.uuid4()),
            duration_seconds=60,
            call_log_id=str(uuid.uuid4()),
            db=db,
        )
        assert result["minutes_deducted"] == 1

    @pytest.mark.asyncio
    async def test_balance_never_goes_below_zero(self):
        wallet = _mock_wallet(minutes=1)
        db = _db_returning(wallet)

        await deduct_minutes_for_call(
            organization_id=str(uuid.uuid4()),
            duration_seconds=600,
            call_log_id=str(uuid.uuid4()),
            db=db,
        )
        assert wallet.minutes_balance == 0

    @pytest.mark.asyncio
    async def test_zero_duration_returns_zero_deduction(self):
        wallet = _mock_wallet(minutes=10)
        db = _db_returning(wallet)

        result = await deduct_minutes_for_call(
            organization_id=str(uuid.uuid4()),
            duration_seconds=0,
            call_log_id=str(uuid.uuid4()),
            db=db,
        )
        assert result["minutes_deducted"] == 0
        assert wallet.minutes_balance     == 10

    @pytest.mark.asyncio
    async def test_creates_debit_transaction(self):
        wallet = _mock_wallet(minutes=10)
        db = _db_returning(wallet)

        await deduct_minutes_for_call(
            organization_id=str(uuid.uuid4()),
            duration_seconds=90,
            call_log_id=str(uuid.uuid4()),
            db=db,
        )
        db.add.assert_called_once()
        tx = db.add.call_args[0][0]
        assert tx.transaction_type == TransactionType.DEBIT


# ─── get_balance ──────────────────────────────────────────────────────────────

class TestGetBalance:

    @pytest.mark.asyncio
    async def test_returns_correct_balance_dict(self):
        wallet = _mock_wallet(minutes=50, rate=2.0)
        wallet.total_minutes_purchased = 200
        wallet.total_minutes_used      = 150
        wallet.total_amount_paid       = 400.0
        db = _db_returning(wallet)

        result = await get_balance(str(uuid.uuid4()), db)

        assert result["minutes_balance"]         == 50
        assert result["rate_per_minute"]         == 2.0
        assert result["total_minutes_purchased"] == 200
        assert result["total_minutes_used"]      == 150
        assert result["total_amount_paid"]       == 400.0


# ─── has_sufficient_balance ───────────────────────────────────────────────────

class TestHasSufficientBalance:

    @pytest.mark.asyncio
    async def test_returns_true_when_balance_positive(self):
        db = _db_returning(_mock_wallet(minutes=10))
        result = await has_sufficient_balance(str(uuid.uuid4()), db)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_balance_zero(self):
        db = _db_returning(_mock_wallet(minutes=0))
        result = await has_sufficient_balance(str(uuid.uuid4()), db)
        assert result is False
