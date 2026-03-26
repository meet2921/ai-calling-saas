import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base

# ✅ Campaign Status Enum
class CampaignStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    running = "running"
    paused = "paused"
    completed = "completed"
    stopped = "stopped"


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False
    )

    bolna_agent_id = Column(String(255), nullable=True, index=True)

    # ✅ Replace is_active with lifecycle status
    status = Column(
        Enum(CampaignStatus, name="campaign_status"),
        nullable=False,
        default=CampaignStatus.draft
    )

    is_processing = Column(Boolean, default=False, nullable=False)
    call_delay_seconds = Column(Integer, default=1)
    scheduled_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relationship
    organization = relationship("Organization")