import uuid
from sqlalchemy import String, Boolean, DateTime, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.models.wallet import Wallet


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name:      Mapped[str]      = mapped_column(String(255), nullable=False)
    slug:      Mapped[str]      = mapped_column(String(100), nullable=False, unique=True, index=True)
    is_active: Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    users  = relationship("User",   back_populates="organization", cascade="all, delete-orphan", lazy="noload")
    wallet = relationship("Wallet", back_populates="organization", uselist=False)

    __table_args__ = (
        Index("ix_organizations_slug_active", "slug", "is_active"),
        {"comment": "Multi-tenant SaaS organizations"},
    )

    def __repr__(self) -> str:
        return f"<Organization slug={self.slug!r} active={self.is_active}>"
