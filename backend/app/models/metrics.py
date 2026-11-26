# Metrics (PHI-minimized, reproducible)

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class MetricFact(Base):
    __tablename__ = "metric_facts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    fact_type = Column(String, nullable=False)
    recorded_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="SET NULL"))
    source_event_id = Column(UUID(as_uuid=True), ForeignKey("care_events.id", ondelete="SET NULL"))
    approved_dimensions = Column(String)  # JSON-encoded dims
    value = Column(String)
    definition_version = Column(String)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    practice = relationship("Practice")
    patient = relationship("Patient")
    source_event = relationship("CareEvent")
