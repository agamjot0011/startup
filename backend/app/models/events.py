# Care events (append-only patient timeline)

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class CareEvent(Base):
    __tablename__ = "care_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=False)
    schema_version = Column(String)
    occurred_at = Column(DateTime)
    recorded_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    actor_type = Column(String)
    actor_id = Column(String)
    privacy_scope = Column(String, nullable=False)
    payload = Column(String)
    correlation_id = Column(String)
    causation_id = Column(String)
    idempotency_key = Column(String)
    prior_event_hash = Column(String)
    event_hash = Column(String)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    practice = relationship("Practice")
    patient = relationship("Patient")
    attachments = relationship("EventAttachment", back_populates="event", cascade="all, delete-orphan")
