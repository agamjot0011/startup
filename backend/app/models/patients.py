# Patient registry and linked user accounts

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("practice_id", "external_id", name="uq_patients_practice_external"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="active")
    given_name = Column(String)
    family_name = Column(String)
    birth_date = Column(String)
    locale = Column(String, default="en")
    timezone = Column(String, default="UTC")
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    updated_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    practice = relationship("Practice", back_populates="patients")
    identifiers = relationship("PatientIdentifier", back_populates="patient", cascade="all, delete-orphan")
    user_link = relationship("PatientUserLink", back_populates="patient", cascade="all, delete-orphan")
    proxy_rel = relationship("ProxyRelationship", back_populates="patient", cascade="all, delete-orphan")
    consents = relationship("Consent", back_populates="patient", cascade="all, delete-orphan")
