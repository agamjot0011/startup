# Patient identifiers (source system, external ID)

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class PatientIdentifier(Base):
    __tablename__ = "patient_identifiers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    source_system = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    valid_from = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    valid_to = Column(DateTime)

    patient = relationship("Patient", back_populates="identifiers")
