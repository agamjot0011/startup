# Rules and routing (deterministic, versioned)

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class RuleSet(Base):
    __tablename__ = "rule_sets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    semantic_key = Column(String, nullable=False)
    trigger_event = Column(String, nullable=False)
    active_version_id = Column(UUID(as_uuid=True), ForeignKey("rule_versions.id", ondelete="SET NULL"))
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    practice = relationship("Practice")
    versions = relationship("RuleVersion", back_populates="rule_set")


class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_set_id = Column(UUID(as_uuid=True), ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    state = Column(String, nullable=False, default="draft")
    definition = Column(String)  # JSON-encoded rule definition
    checksum = Column(String, nullable=False)
    author = Column(String)
    reason = Column(String)
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    rule_set = relationship("RuleSet", back_populates="versions")
    approvals = relationship("RuleApproval", back_populates="rule_version", cascade="all, delete-orphan")
    executions = relationship("RuleExecution", back_populates="rule_version", cascade="all, delete-orphan")


class RuleApproval(Base):
    __tablename__ = "rule_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_version_id = Column(UUID(as_uuid=True), ForeignKey("rule_versions.id", ondelete="CASCADE"), nullable=False)
    approver_id = Column(String)
    decision = Column(String, nullable=False)  # approve, reject
    approved_checksum = Column(String)
    reason = Column(String)
    approved_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    rule_version = relationship("RuleVersion", back_populates="approvals")


class RuleExecution(Base):
    __tablename__ = "rule_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_version_id = Column(UUID(as_uuid=True), ForeignKey("rule_versions.id", ondelete="CASCADE"), nullable=False)
    trigger_event_id = Column(UUID(as_uuid=True), ForeignKey("care_events.id", ondelete="SET NULL"))
    input_fact_hash = Column(String)
    output_plan_hash = Column(String)
    state = Column(String, nullable=False)
    explanation_codes = Column(String)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    rule_version = relationship("RuleVersion", back_populates="executions")
