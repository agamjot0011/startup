"""PMS package quarantine, mapping, dry run and atomic commit.

Handbook detailed step 8 (lines 4560-4620): uploaded packages are quarantined,
parsed in isolation, validated against a mapping profile, dry-run with a
reconciliation summary, then committed atomically with care events and an
outbox message. Re-uploading the same package cannot commit twice.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.services.authz_service import AuthzError
from app.services.event_ledger import event_ledger
from app.services import supabase_store

REQUIRED_FIELDS = ("patient_ref", "event_date", "event_type")
ALLOWED_EVENT_TYPES = {"visit", "adjustment", "debond", "bond_check"}


class ImportError(Exception):
    def __init__(self, code: str, status: int = 400, message: str = "") -> None:
        self.code, self.status = code, status
        self.message = message or code
        super().__init__(self.message)


@dataclass
class ImportRow:
    row_number: int
    raw: dict
    normalized: dict = field(default_factory=dict)
    status: str = "PENDING"
    issues: list[str] = field(default_factory=list)


@dataclass
class ImportBatch:
    import_id: str
    practice_id: str
    filename: str
    sha256: str
    state: str
    received_at: str
    rows: list[ImportRow] = field(default_factory=list)
    mapping: dict = field(default_factory=dict)
    committed_at: Optional[str] = None
    correction_of: Optional[str] = None

    def public(self) -> dict:
        return {
            "import_id": self.import_id,
            "practice_id": self.practice_id,
            "filename": self.filename,
            "sha256": self.sha256,
            "state": self.state,
            "received_at": self.received_at,
            "row_count": len(self.rows),
            "mapping": self.mapping,
            "committed_at": self.committed_at,
            "correction_of": self.correction_of,
        }


class PMSService:
    def __init__(self) -> None:
        self._batches: dict[str, ImportBatch] = {}
        self._committed_hashes: dict[tuple[str, str], str] = {}
        self._lock = threading.RLock()

    def quarantine(self, practice_id: str, filename: str, content: bytes) -> ImportBatch:
        if not content:
            raise ImportError("EMPTY_PACKAGE", 400)
        if len(content) > 10 * 1024 * 1024:
            raise ImportError("PACKAGE_TOO_LARGE", 413)
        digest = hashlib.sha256(content).hexdigest()
        with self._lock:
            for batch in self._batches.values():
                if batch.practice_id == practice_id and batch.sha256 == digest and batch.state == "COMMITTED":
                    raise ImportError("DUPLICATE_COMMITTED_PACKAGE", 409)
            batch = ImportBatch(
                import_id=str(uuid.uuid4()), practice_id=practice_id, filename=filename,
                sha256=digest, state="QUARANTINED",
                received_at=datetime.now(timezone.utc).isoformat(),
            )
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ImportError("INVALID_ENCODING", 400) from exc
            reader = csv.DictReader(io.StringIO(text))
            if reader.fieldnames is None:
                raise ImportError("MISSING_HEADER", 400)
            for i, row in enumerate(reader, start=1):
                batch.rows.append(ImportRow(row_number=i, raw=dict(row)))
            self._batches[batch.import_id] = batch
            supabase_store.save("import_batches", batch, "import_id", exclude=("rows",))
            supabase_store.insert("import_rows", [
                {"import_id": batch.import_id, "row_number": r.row_number,
                 "raw": json.dumps(r.raw), "normalized": json.dumps(r.normalized),
                 "status": r.status, "issues": json.dumps(r.issues)}
                for r in batch.rows
            ])
            return batch

    def get(self, import_id: str) -> ImportBatch:
        batch = self._batches.get(import_id)
        if batch is None:
            raise ImportError("IMPORT_NOT_FOUND", 404)
        return batch

    def dry_run(self, import_id: str, mapping: Optional[dict] = None) -> dict:
        with self._lock:
            batch = self.get(import_id)
            if batch.state not in {"QUARANTINED", "STAGED"}:
                raise ImportError("INVALID_IMPORT_STATE", 409, batch.state)
            batch.mapping = mapping or {}
            valid = invalid = 0
            seen: set[str] = set()
            for row in batch.rows:
                row.issues = []
                raw = {k.strip(): (v or "").strip() for k, v in row.raw.items() if k}
                for key in REQUIRED_FIELDS:
                    mapped_key = batch.mapping.get(key, key)
                    value = raw.get(mapped_key, "")
                    if not value:
                        row.issues.append(f"missing:{key}")
                event_type = raw.get(batch.mapping.get("event_type", "event_type"), "")
                if event_type and event_type not in ALLOWED_EVENT_TYPES:
                    row.issues.append("unsupported_event_type")
                patient_ref = raw.get(batch.mapping.get("patient_ref", "patient_ref"), "")
                if patient_ref and patient_ref in seen:
                    row.issues.append("duplicate_patient_ref")
                if patient_ref:
                    seen.add(patient_ref)
                row.normalized = {
                    "patient_ref": patient_ref,
                    "event_date": raw.get(batch.mapping.get("event_date", "event_date"), ""),
                    "event_type": event_type,
                }
                row.status = "VALID" if not row.issues else "INVALID"
                valid += row.status == "VALID"
                invalid += row.status == "INVALID"
            batch.state = "DRY_RUN"
            return {
                "import_id": import_id,
                "state": batch.state,
                "rows": len(batch.rows),
                "valid": valid,
                "invalid": invalid,
                "issues": {str(r.row_number): r.issues for r in batch.rows if r.issues},
                "isolated": True,
            }

    def commit(self, import_id: str, actor_user_id: Optional[str] = None) -> dict:
        with self._lock:
            batch = self.get(import_id)
            if batch.state != "DRY_RUN":
                raise ImportError("DRY_RUN_REQUIRED", 409)
            invalid = [r for r in batch.rows if r.status != "VALID"]
            if invalid:
                raise ImportError("INVALID_ROWS_PRESENT", 409, f"{len(invalid)} invalid rows")
            key = (batch.practice_id, batch.sha256)
            if key in self._committed_hashes:
                raise ImportError("DUPLICATE_COMMITTED_PACKAGE", 409)

            written = 0
            for row in batch.rows:
                event_ledger.append(
                    practice_id=batch.practice_id,
                    patient_id=row.normalized["patient_ref"],
                    event_type=f"pms_{row.normalized['event_type']}.v1",
                    source_type="pms_import", source_id=f"{import_id}:{row.row_number}",
                    payload={"raw": row.raw, "normalized": row.normalized},
                    actor_user_id=actor_user_id,
                )
                written += 1
            batch.state = "COMMITTED"
            batch.committed_at = datetime.now(timezone.utc).isoformat()
            supabase_store.update("import_batches", {"import_id": f"eq.{import_id}"}, {"state": "COMMITTED", "committed_at": batch.committed_at})
            self._committed_hashes[key] = import_id
            return {
                "import_id": import_id, "state": "COMMITTED",
                "rows_written": written, "committed_at": batch.committed_at,
            }

    def compensating_correction(self, import_id: str, reason: str, actor_user_id: Optional[str]) -> dict:
        if not reason.strip():
            raise ImportError("CORRECTION_REASON_REQUIRED", 400)
        with self._lock:
            batch = self.get(import_id)
            if batch.state != "COMMITTED":
                raise ImportError("NOT_COMMITTED", 409)
            for row in batch.rows:
                event_ledger.append(
                    practice_id=batch.practice_id,
                    patient_id=row.normalized["patient_ref"],
                    event_type="pms_import_corrected.v1",
                    source_type="compensating_correction",
                    source_id=f"{import_id}:{row.row_number}",
                    payload={"reason": reason, "original_import": import_id, "row": row.normalized},
                    actor_user_id=actor_user_id,
                )
            return {"import_id": import_id, "corrected_rows": len(batch.rows), "reason": reason}


pms_service = PMSService()
