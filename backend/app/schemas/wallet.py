from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.models.wallet import TransactionType


class WalletResponse(BaseModel):
    id: UUID
    organization_id: UUID
    minutes_balance: int
    rate_per_minute: float
    total_minutes_purchased: int
    total_minutes_used: int
    total_amount_paid: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WalletTransactionResponse(BaseModel):
    id: UUID
    wallet_id: UUID
    transaction_type: TransactionType
    minutes: int
    amount_inr: float
    rate_per_minute: float
    balance_after: int
    description: str | None
    call_log_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WalletCreditRequest(BaseModel):
    amount_inr: float
    rate_per_minute: float
    description: str | None = None
