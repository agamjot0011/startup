# Practices: each practice is a separate tenant

from sqlalchemy import Column, String, Text, JSON, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class Practice(Base):
    __tablename__ = "practices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    timezone = Column(String, nullable=False, default="UTC")
    settings = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    updated_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    memberships = relationship("PracticeMembership", back_populates="practice", cascade="all, delete-orphan")
    patients = relationship("Patient", back_populates="practice", cascade="all, delete-orphan")
