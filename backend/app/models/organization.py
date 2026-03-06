# import uuid
# from sqlalchemy import String, Boolean, DateTime, func
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.orm import Mapped, mapped_column, relationship
# from app.models.base import Base
# import uuid
# from datetime import datetime

# class Organization(Base):
#     __tablename__ = "organizations"

#     id: Mapped[uuid.UUID] = mapped_column(
#         UUID(as_uuid=True),
#         primary_key=True,
#         default=uuid.uuid4
#     )
#     name: Mapped[str] = mapped_column(String(255), nullable=False)
#     slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
#     is_active: Mapped[bool] = mapped_column(Boolean, default=True)
#     created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

#     # One org has many users
#     users = relationship("User", back_populates="organization", cascade="all, delete-orphan")

#     def __repr__(self):
#         return f"<Organization {self.name}>"

"""
app/models/organization.py

Multi-tenant SaaS Organization model.

Design decisions:
  - slug is NOT globally unique — same company name can register multiple orgs
    (e.g. "acme" for acme.io and acme.co). Slug is a human-readable label only.
  - slug is indexed for fast lookup during login (WHERE slug = ?)
  - Soft delete via is_active — never hard delete orgs in SaaS
  - cascade="all, delete-orphan" → deleting org purges all its users (use with caution)
"""

import uuid
from sqlalchemy import String, Boolean, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base
import uuid
from datetime import datetime
from app.models.wallet import Wallet

class Organization(Base):
    __tablename__ = "organizations"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Fields ────────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable org name, e.g. 'Acme Corp'",
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        # NOT unique globally — same slug can exist in different contexts.
        # Login uses org_slug to scope the user lookup, not as a unique key.
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

    # ── Relationships ─────────────────────────────────────────────────────────
    users = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="noload",   # always explicit — never implicit N+1 loads
    )

    # ── Table-level indexes ───────────────────────────────────────────────────
    __table_args__ = (
        # Login query: WHERE slug = ? AND is_active = true
        Index("ix_organizations_slug", "slug"),
        Index("ix_organizations_slug_active", "slug", "is_active"),
        {
            "comment": "Multi-tenant SaaS organizations. One org → many users."
        },
    )
    # One org has many users
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    wallet = relationship("Wallet", back_populates="organization", uselist=False)

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug!r} active={self.is_active}>"