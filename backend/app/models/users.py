# User profiles. Authentication credentials remain with Supabase Auth.

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String)
    full_name = Column(String)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    updated_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    memberships = relationship("PracticeMembership", back_populates="user", cascade="all, delete-orphan")
