# Proxy relationships (verified representative authority)

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class ProxyRelationship(Base):
    __tablename__ = "proxy_relationships"
    __table_args__ = (
        UniqueConstraint("patient_id", "proxy_user_id", name="uq_proxy_patient_user"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    proxy_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    relationship_code = Column(String, nullable=False)
    authority_scopes = Column(String, nullable=False)  # JSON-encoded list
    verification_method = Column(String, nullable=False)
    policy_version_id = Column(String)
    status = Column(String, nullable=False, default="active")
    effective_from = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    effective_to = Column(DateTime)
    revoked_at = Column(DateTime)
    revoked_reason_code = Column(String)

    patient = relationship("Patient", back_populates="proxy_rel")
    proxy_user = relationship("User")
