
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.wallet import Wallet, WalletTransaction, TransactionType
from app.services.wallet_service import get_balance


router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.get("/balance")
async def get_wallet_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns current wallet balance"""
    return await get_balance(
        str(current_user.organization_id),
        db
    )


@router.get("/transactions")
async def get_wallet_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns full transaction history"""

    wallet_result = await db.execute(
        select(Wallet).where(
            Wallet.organization_id == current_user.organization_id
        )
    )
    wallet = wallet_result.scalar_one_or_none()

    if not wallet:
        return {"transactions": [], "total": 0}

    tx_result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
    )
    transactions = tx_result.scalars().all()

    return {
        "total": len(transactions),
        "transactions": [
            {
                "id": str(tx.id),
                "type": tx.transaction_type,
                "minutes": tx.minutes,
                "amount_inr": tx.amount_inr,
                "rate_per_minute": tx.rate_per_minute,
                "balance_after": tx.balance_after,
                "description": tx.description,
                "call_log_id": str(tx.call_log_id) if tx.call_log_id else None,
                "created_at": str(tx.created_at),
            }
            for tx in transactions
        ]
    }


@router.get("/summary")
@router.get("/summary")
async def get_wallet_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns wallet summary for dashboard"""

    wallet_result = await db.execute(
        select(Wallet).where(
            Wallet.organization_id == current_user.organization_id
        )
    )
    wallet = wallet_result.scalar_one_or_none()

    if not wallet:
        return {
            "minutes_balance": 0,
            "rate_per_minute": 0,
            "total_minutes_purchased": 0,
            "total_minutes_used": 0,
            "total_amount_paid": 0,
            "estimated_cost_remaining": 0,
            "billed_minutes": 0,
        }

    billed_result = await db.execute(
        select(func.coalesce(func.sum(WalletTransaction.minutes), 0))
        .where(WalletTransaction.wallet_id == wallet.id)
        .where(WalletTransaction.transaction_type == TransactionType.DEBIT)
    )
    billed_minutes = billed_result.scalar()

    estimated_cost_remaining = round(
        wallet.minutes_balance * wallet.rate_per_minute, 2
    )

    return {
        "minutes_balance": wallet.minutes_balance,
        "rate_per_minute": wallet.rate_per_minute,
        "total_minutes_purchased": wallet.total_minutes_purchased,
        "total_minutes_used": wallet.total_minutes_used,
        "total_amount_paid": wallet.total_amount_paid,
        "estimated_cost_remaining": estimated_cost_remaining,
        "billed_minutes": billed_minutes,
<<<<<<< HEAD
    }
=======
    }
>>>>>>> 2b26161fa37ee85b0d6248c4f9853399ba71fd6c
