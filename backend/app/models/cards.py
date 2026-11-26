# Cards (role inboxes, card lifecycle, loops)

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class Card(Base):
    __tablename__ = "cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    source_event_id = Column(UUID(as_uuid=True), ForeignKey("care_events.id", ondelete="SET NULL"))
    card_type = Column(String, nullable=False)
    recipient_role = Column(String)
    recipient_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    owner_membership_id = Column(UUID(as_uuid=True), ForeignKey("practice_memberships.id", ondelete="SET NULL"))
    absolute_deadline = Column(DateTime)
    timezone = Column(String, default="UTC")
    rule_version_id = Column(String)
    content_version_id = Column(String)
    privacy_scope = Column(String, nullable=False)
    status = Column(String, nullable=False, default="available")
    mandatory_flag = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime)
    closed_at = Column(DateTime)
    row_version = Column(Numeric(asdecimal=False), nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    updated_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    practice = relationship("Practice")
    patient = relationship("Patient")
    source_event = relationship("CareEvent")
    owner_membership = relationship("PracticeMembership")
    acknowledgements = relationship("CardAcknowledgement", back_populates="card", cascade="all, delete-orphan")
    results = relationship("CardResult", back_populates="card", cascade="all, delete-orphan")
    escalations = relationship("CardEscalation", back_populates="card", cascade="all, delete-orphan")


class CardAcknowledgement(Base):
    __tablename__ = "card_acknowledgements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)
    card_version = Column(Numeric(asdecimal=False), nullable=False)
    actor_id = Column(String)
    acknowledged_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    channel = Column(String)

    card = relationship("Card", back_populates="acknowledgements")


class CardResult(Base):
    __tablename__ = "card_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)
    result_code = Column(String, nullable=False)
    payload = Column(String)
    actor_id = Column(String)
    recorded_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    verifier_id = Column(String)

    card = relationship("Card", back_populates="results")


class CardEscalation(Base):
    __tablename__ = "card_escalations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)
    policy_version_id = Column(String)
    milestone = Column(String, nullable=False)
    due_at = Column(DateTime)
    executed_at = Column(DateTime)
    action = Column(String)
    recipient_id = Column(String)
    disposition = Column(String)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    card = relationship("Card", back_populates="escalations")
