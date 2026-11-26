# PMS imports (quarantine, dry-run, commit, reconciliation)

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
import uuid


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id = Column(UUID(as_uuid=True), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False)
    source_system = Column(String, nullable=False)
    source_tenant_id = Column(String)
    package_hash = Column(String, nullable=False)
    mapping_version = Column(String)
    mode = Column(String, default="daily")
    state = Column(String, nullable=False, default="upload")
    object_reference = Column(String)
    export_time = Column(DateTime)
    upload_time = Column(DateTime)
    commit_time = Column(DateTime)
    uploader = Column(String)
    row_count = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())
    updated_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    practice = relationship("Practice")
    rows = relationship("ImportRow", back_populates="batch", cascade="all, delete-orphan")
    events = relationship("ImportEvent", back_populates="import_batch", cascade="all, delete-orphan")


class ImportRow(Base):
    __tablename__ = "import_rows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False)
    file = Column(String, nullable=False)
    row_number = Column(Integer, nullable=False)
    entity_type = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    source_updated_at = Column(DateTime)
    row_hash = Column(String)
    parsed_payload = Column(String)
    planned_action = Column(String)
    result_code = Column(String)
    error_detail = Column(String)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    batch = relationship("ImportBatch", back_populates="rows")


class ImportEvent(Base):
    __tablename__ = "import_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(String)
    source = Column(String)
    row_hash = Column(String)
    created_at = Column(DateTime, nullable=False, default=lambda: __import__("datetime").datetime.now())

    import_batch = relationship("ImportBatch", back_populates="events")
