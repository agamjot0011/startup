# Practice memberships (a user can belong to multiple practices)

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class PracticeMembership(Base):
    __tablename__ = "practice_memberships"
    __table_args__ = (
        UniqueConstraint("practice_id", "user_id", name="uq_memberships_practice_user"),
        UniqueConstraint("id", "practice_id", name="uq_memberships_id_practice"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="invited")
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    updated_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    practice = relationship("Practice", back_populates="memberships")
    user = relationship("User", back_populates="memberships")
    roles = relationship("MembershipRole", back_populates="membership", cascade="all, delete-orphan")
