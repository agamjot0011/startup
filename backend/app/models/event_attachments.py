# Event attachments (linked to care events)

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class EventAttachment(Base):
    __tablename__ = "event_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("care_events.id", ondelete="CASCADE"), nullable=False)
    attachment_id = Column(UUID(as_uuid=True), ForeignKey("attachments.id", ondelete="CASCADE"), nullable=False)
    relation_code = Column(String, nullable=False)

    event = relationship("CareEvent", back_populates="attachments")
    attachment = relationship("Attachment")
