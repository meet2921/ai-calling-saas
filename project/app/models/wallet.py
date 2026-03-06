import uuid
import enum
from datetime import datetime
from sqlalchemy import Integer, Float, ForeignKey, DateTime, Enum as SAEnum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class TransactionType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT  = "debit"


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    minutes_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rate_per_minute: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    total_minutes_purchased: Mapped[int] = mapped_column(Integer, default=0)
    total_minutes_used: Mapped[int] = mapped_column(Integer, default=0)
    total_amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization = relationship("Organization", back_populates="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType), nullable=False
    )
    amount_inr: Mapped[float] = mapped_column(Float, default=0.0)
    rate_per_minute: Mapped[float] = mapped_column(Float, nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    call_log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    wallet = relationship("Wallet", back_populates="transactions")