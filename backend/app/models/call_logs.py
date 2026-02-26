from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import Base


class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)

    user_number = Column(String, nullable=False)

    duration = Column(Integer, default=0)  # seconds
    cost = Column(Float, default=0.0)
    status = Column(String, nullable=True)

    recording_url = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)

    scheduled_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow)

    username = Column(String, nullable=True)

    interest_level = Column(String, nullable=True)
    appointment_booked = Column(Boolean, default=False)
    appointment_date = Column(DateTime, nullable=True)
    appointment_mode = Column(String, nullable=True)

    customer_sentiment = Column(String, nullable=True)

    final_call_summary = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    transfer_call = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("Campaign", backref="call_logs")
    lead = relationship("Lead", backref="call_logs")