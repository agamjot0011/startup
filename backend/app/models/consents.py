# Purpose-scoped consents and assent

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = (
        UniqueConstraint("patient_id", "consent_kind", name="uq_consent_patient_kind"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    consent_kind = Column(String, nullable=False)
    decision = Column(String, nullable=False)  # permit, deny, withdraw
    source_content_version_id = Column(String)
    source_document_sha256 = Column(String)
    locale = Column(String, default="en")
    effective_from = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    effective_to = Column(DateTime)
    supersedes_id = Column(UUID(as_uuid=True), ForeignKey("consents.id", ondelete="SET NULL"))

    patient = relationship("Patient", back_populates="consents")
