import math
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.wallet import Wallet, WalletTransaction, TransactionType

logger = logging.getLogger(__name__)


async def get_or_create_wallet(
    organization_id: str,
    db: AsyncSession
) -> Wallet:
    result = await db.execute(
        select(Wallet).where(Wallet.organization_id == organization_id)
    )
    wallet = result.scalar_one_or_none()

    if wallet:
        return wallet

    wallet = Wallet(
        organization_id=organization_id,
        minutes_balance=0,
        rate_per_minute=0.50,
        total_minutes_purchased=0,
        total_minutes_used=0,
        total_amount_paid=0.0,
    )
    db.add(wallet)
    await db.flush()
    logger.info(f"Created new wallet for org {organization_id}")
    return wallet


async def credit_wallet(
    organization_id: str,
    amount_inr: float,
    rate_per_minute: float,
    description: str,
    db: AsyncSession
) -> dict:
    wallet = await get_or_create_wallet(organization_id, db)
    wallet.rate_per_minute = rate_per_minute

    minutes_to_add = math.floor(amount_inr / rate_per_minute) if rate_per_minute > 0 else 0

    if minutes_to_add <= 0:
        raise ValueError(
            f"Amount ₹{amount_inr} is too small "
            f"for rate ₹{rate_per_minute}/min"
        )

    old_balance = wallet.minutes_balance
    wallet.minutes_balance         += minutes_to_add
    wallet.total_minutes_purchased += minutes_to_add
    wallet.total_amount_paid       += amount_inr

    transaction = WalletTransaction(
        wallet_id=wallet.id,
        transaction_type=TransactionType.CREDIT,
        amount_inr=amount_inr,
        rate_per_minute=rate_per_minute,
        minutes=minutes_to_add,
        balance_after=wallet.minutes_balance,
        description=description
    )
    db.add(transaction)

    logger.info(
        f"Wallet credited | Org: {organization_id} | "
        f"₹{amount_inr} → {minutes_to_add} min | "
        f"Balance: {old_balance} → {wallet.minutes_balance}"
    )

    return {
        "minutes_added": minutes_to_add,
        "old_balance": old_balance,
        "new_balance": wallet.minutes_balance,
        "amount_inr": amount_inr,
        "rate_per_minute": rate_per_minute,
    }


async def deduct_minutes_for_call(
    organization_id: str,
    duration_seconds: float,
    call_log_id: str,
    db: AsyncSession
) -> dict:
    # SELECT FOR UPDATE prevents concurrent deductions from the same wallet
    result = await db.execute(
        select(Wallet)
        .where(Wallet.organization_id == organization_id)
        .with_for_update()
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        wallet = await get_or_create_wallet(organization_id, db)

    if duration_seconds <= 0:
        return {
            "minutes_deducted": 0,
            "new_balance": wallet.minutes_balance
        }

    billable_minutes = math.ceil(duration_seconds / 60)
    old_balance = wallet.minutes_balance

    wallet.minutes_balance    = max(0, wallet.minutes_balance - billable_minutes)
    wallet.total_minutes_used += billable_minutes

    transaction = WalletTransaction(
        wallet_id=wallet.id,
        transaction_type=TransactionType.DEBIT,
        amount_inr=0.0,
        rate_per_minute=wallet.rate_per_minute,
        minutes=billable_minutes,
        balance_after=wallet.minutes_balance,
        call_log_id=call_log_id,
        description=(
            f"Call {round(duration_seconds)}s "
            f"→ {billable_minutes} min deducted"
        )
    )
    db.add(transaction)

    logger.warning(
        f"Wallet debited | Org: {organization_id} | "
        f"Duration: {duration_seconds}s | "
        f"Deducted: {billable_minutes} min | "
        f"Balance: {old_balance} → {wallet.minutes_balance}"
    )

    return {
        "minutes_deducted": billable_minutes,
        "old_balance": old_balance,
        "new_balance": wallet.minutes_balance,
        "duration_seconds": duration_seconds,
    }


async def get_balance(
    organization_id: str,
    db: AsyncSession
) -> dict:
    wallet = await get_or_create_wallet(organization_id, db)
    return {
        "minutes_balance": wallet.minutes_balance,
        "rate_per_minute": wallet.rate_per_minute,
        "total_minutes_purchased": wallet.total_minutes_purchased,
        "total_minutes_used": wallet.total_minutes_used,
        "total_amount_paid": wallet.total_amount_paid,
    }


async def has_sufficient_balance(
    organization_id: str,
    db: AsyncSession
) -> bool:
    result = await db.execute(
        select(Wallet)
        .where(Wallet.organization_id == organization_id)
        .with_for_update()
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        return False
    return wallet.minutes_balance > 0
