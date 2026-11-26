# Membership roles (orthodontist, clinical_assistant, front_desk, practice_manager)

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class MembershipRole(Base):
    __tablename__ = "membership_roles"
    __table_args__ = (
        UniqueConstraint("membership_id", "role", name="uq_roles_membership_role"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    membership_id = Column(UUID(as_uuid=True), ForeignKey("practice_memberships.id", ondelete="CASCADE"), nullable=False)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    membership = relationship("PracticeMembership", back_populates="roles")
