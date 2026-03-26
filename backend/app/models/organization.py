import uuid
from sqlalchemy import String, Boolean, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable org name, e.g. 'Acme Corp'",
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="URL-friendly label used in login form. Not globally unique.",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Soft delete flag. Inactive orgs block login for all their users.",
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    users = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    wallet = relationship(
        "Wallet",
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_organizations_slug", "slug"),
        Index("ix_organizations_slug_active", "slug", "is_active"),
        {"comment": "Multi-tenant SaaS organizations. One org → many users."},
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug!r} active={self.is_active}>"
