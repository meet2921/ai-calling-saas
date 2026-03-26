import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    DateTime,
    Enum,
    Integer,
    Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB as JSON
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from app.models.base import Base


class CallStatus(str, enum.Enum):
    QUEUED = "queued"
    INITIATED = "initiated"
    RINGING = "ringing"
    CONNECTED = "connected"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    CANCELED = "canceled"


class Call(Base):
    __tablename__ = "calls"

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

    lead_id = Column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    bolna_call_id = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True
    )

    status = Column(
        Enum(CallStatus, name="call_status"),
        nullable=False,
        default=CallStatus.QUEUED
    )

    attempt_number = Column(
        Integer,
        nullable=False
    )

    duration_seconds = Column(Integer, nullable=True)

    transcript = Column(Text, nullable=True)
    recording_url = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    campaign = relationship(
        "Campaign",
        backref=backref("calls", cascade="all, delete-orphan")
    )
    lead = relationship(
        "Lead",
        backref=backref("calls", cascade="all, delete-orphan")
    )
    organization = relationship("Organization")

    provider_response = Column(JSON, nullable=True)