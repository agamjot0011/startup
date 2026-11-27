# Content governance (versioned, immutable)

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    semantic_key = Column(String, nullable=False)
    content_class = Column(String, nullable=False)
    audience = Column(String, nullable=False)
    purpose = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    practice = relationship("Practice")
    versions = relationship("ContentVersion", back_populates="content_item", cascade="all, delete-orphan")
    approvals = relationship("ContentApproval", back_populates="content_version", cascade="all, delete-orphan")


class ContentVersion(Base):
    __tablename__ = "content_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    locale = Column(String, nullable=False)
    state = Column(String, nullable=False, default="draft")
    body = Column(String, nullable=False)  # JSON-encoded content body
    checksum = Column(String, nullable=False)
    readability = Column(String)
    author = Column(String)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    content_item = relationship("ContentItem", back_populates="versions")
    approvals = relationship("ContentApproval", back_populates="content_version", cascade="all, delete-orphan")


class ContentApproval(Base):
    __tablename__ = "content_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_version_id = Column(UUID(as_uuid=True), ForeignKey("content_versions.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(String)
    review_type = Column(String, nullable=False)  # clinical, legal, accessibility
    decision = Column(String, nullable=False)
    approved_checksum = Column(String)
    reviewed_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    content_version = relationship("ContentVersion", back_populates="approvals")
