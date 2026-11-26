# Appointments (read-only PMS mirror)

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    source_system = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    start_at = Column(DateTime)
    end_at = Column(DateTime)
    source_timezone = Column(String, default="UTC")
    visit_type_code = Column(String)
    provider_source_id = Column(String)
    import_batch_id = Column(String)
    source_updated_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    updated_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    practice = relationship("Practice")
    patient = relationship("Patient")
