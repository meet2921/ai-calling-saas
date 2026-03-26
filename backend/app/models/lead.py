import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, ForeignKey,
    DateTime, SmallInteger,
    Enum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from app.models.base import Base

class LeadStatus(str, PyEnum):
    PENDING = "pending"
    QUEUED = "queued"
    CALLING = "calling"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"


class Lead(Base):
    __tablename__ = "leads"

    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "phone",
            name="uq_campaign_phone"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    phone = Column(String(30), nullable=False)

    status = Column(
        Enum(LeadStatus, name="lead_status"),
        default=LeadStatus.PENDING,
        nullable=False
    )

    attempts = Column(SmallInteger, default=0)

    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    custom_fields = Column(JSONB, default=dict)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    campaign = relationship("Campaign")

    external_call_id = Column(String, nullable=True, index=True)
    last_called = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # seconds of last call
