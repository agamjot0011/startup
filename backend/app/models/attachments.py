# Attachments (secure photo storage)

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    object_key = Column(String, nullable=False)
    purpose_code = Column(String, nullable=False)
    declared_mime = Column(String)
    detected_mime = Column(String)
    byte_size = Column(Integer)
    sha256 = Column(String, nullable=False)
    privacy_scope = Column(String, nullable=False)
    status = Column(String, nullable=False, default="upload_pending")
    malware_detected = Column(Boolean, default=False)
    uploaded_by = Column(String)
    uploaded_at = Column(DateTime)
    available_at = Column(DateTime)
    retention_class = Column(String)
    tombstone_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    event_links = relationship("EventAttachment", back_populates="attachment", cascade="all, delete-orphan")
