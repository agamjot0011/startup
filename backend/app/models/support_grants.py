# Support grants (scoped, ticketed)

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class SupportGrant(Base):
    __tablename__ = "support_grants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    support_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticket_reference = Column(String)
    purpose_code = Column(String, nullable=False)
    scope_json = Column(String)  # JSON-encoded scope
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    second_approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    effective_from = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    effective_to = Column(DateTime)
    revoked_at = Column(DateTime)

    practice = relationship("Practice")
    support_user = relationship("User")
