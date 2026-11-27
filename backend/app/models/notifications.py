# Notifications (in-app, generic external prompts)

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel_code = Column(String, nullable=False)
    destination_ref = Column(String)
    status = Column(String, nullable=False, default="active")
    timezone = Column(String, default="UTC")
    quiet_start = Column(String)
    quiet_end = Column(String)
    consent_id = Column(UUID(as_uuid=True), ForeignKey("consents.id", ondelete="SET NULL"))
    row_version = Column(Numeric(asdecimal=False), nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    updated_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    practice = relationship("Practice")
    patient = relationship("Patient")
    user = relationship("User")
    consent = relationship("Consent")


class NotificationCommand(Base):
    __tablename__ = "notification_commands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    recipient_id = Column(String)
    channel = Column(String, nullable=False)
    purpose = Column(String, nullable=False)
    template_version_id = Column(String, nullable=False)
    scanner_version = Column(String)
    not_before = Column(DateTime)
    state = Column(String, nullable=False, default="held")
    dedupe_key = Column(String)
    payload_hash = Column(String)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    dispatched_at = Column(DateTime)

    practice = relationship("Practice")
    patient = relationship("Patient")


class NotificationAttempt(Base):
    __tablename__ = "notification_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    command_id = Column(UUID(as_uuid=True), ForeignKey("notification_commands.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String)
    provider_ref = Column(String)
    attempt_number = Column(Integer, nullable=False)
    state = Column(String, nullable=False)
    error_code = Column(String)
    attempt_time = Column(DateTime)

    command = relationship("NotificationCommand")
