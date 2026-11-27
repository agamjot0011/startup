# Scheduled jobs, outbox, idempotency, audit

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    job_type = Column(String, nullable=False)
    entity_type = Column(String)
    entity_id = Column(UUID(as_uuid=True))
    milestone_version = Column(String)
    run_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    status = Column(String, nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    lease_owner = Column(String)
    lease_expires_at = Column(DateTime)
    last_reason = Column(String)
    dedupe_key = Column(String)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    updated_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    practice = relationship("Practice")


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=False)
    aggregate_type = Column(String, nullable=False)
    aggregate_id = Column(UUID(as_uuid=True))
    payload = Column(String)
    status = Column(String, nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    dispatched_at = Column(DateTime)

    practice = relationship("Practice")


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    route_key = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=False)
    request_hash = Column(String, nullable=False)
    status = Column(String, nullable=False)
    response_status = Column(Integer)
    response_reference = Column(String)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    expires_at = Column(DateTime)

    practice = relationship("Practice")
    user = relationship("User")


class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(UUID(as_uuid=True))
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="SET NULL"))
    purpose_code = Column(String)
    policy_reference = Column(String)
    outcome_code = Column(String)
    reason_code = Column(String)
    correlation_id = Column(UUID(as_uuid=True))
    source_network_prefix = Column(String)
    release_id = Column(String)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    practice = relationship("Practice")
    user = relationship("User")
    patient = relationship("Patient")
