"""Visit brief snapshots, doctor sign-off and supersession — handbook 17.1/17.3.

A signature freezes the exact snapshot hash. Later changes append a new brief
version and a supersession record; the signed artifact is never edited.
No generated clinical conclusion is accepted into a source set.
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.services.authz_service import AuthzError
from app.services.event_ledger import event_ledger
from app.services.session_service import SessionRecord, session_store
from app.services import supabase_store


def _hash(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@dataclass
class Signature:
    signature_id: str
    brief_id: str
    signer_user_id: str
    signed_at: str
    snapshot_hash: str
    attestation: str
    assurance: str


@dataclass
class VisitBrief:
    brief_id: str
    appointment_id: str
    practice_id: str
    patient_id: str
    events_since_cutoff: list[dict]
    source_watermark: str
    snapshot_hash: str
    generated_at: str
    row_version: int = 1
    superseded_by: Optional[str] = None
    signatures: list[Signature] = field(default_factory=list)

    def public(self) -> dict:
        return {
            "brief_id": self.brief_id,
            "appointment_id": self.appointment_id,
            "patient_id": self.patient_id,
            "events_since_cutoff": self.events_since_cutoff,
            "source_watermark": self.source_watermark,
            "snapshot_hash": self.snapshot_hash,
            "generated_at": self.generated_at,
            "row_version": self.row_version,
            "superseded_by": self.superseded_by,
            "signed": len(self.signatures) > 0,
        }


class BriefError(Exception):
    def __init__(self, code: str, status: int = 400, message: str = "") -> None:
        self.code, self.status = code, status
        self.message = message or code
        super().__init__(self.message)


class BriefService:
    def __init__(self) -> None:
        self._briefs: dict[str, VisitBrief] = {}
        self._signatures: dict[str, Signature] = {}
        self._lock = threading.RLock()

    @staticmethod
    def validate_sources(events: list[dict]) -> None:
        for event in events:
            if "generated_conclusion" in event or "machine_urgency" in event:
                raise BriefError("GENERATED_CONCLUSION_PROHIBITED", 400)

    def generate(
        self,
        *,
        appointment_id: str,
        practice_id: str,
        patient_id: str,
        events: list[dict],
        actor: Optional[SessionRecord] = None,
    ) -> VisitBrief:
        self.validate_sources(events)
        with self._lock:
            snapshot = {"appointment_id": appointment_id, "patient_id": patient_id, "events": events}
            brief = VisitBrief(
                brief_id=str(uuid.uuid4()), appointment_id=appointment_id,
                practice_id=practice_id, patient_id=patient_id,
                events_since_cutoff=events,
                source_watermark=_hash({"events": events}),
                snapshot_hash=_hash(snapshot),
                generated_at=datetime.now(timezone.utc).isoformat(),
            )
            self._briefs[brief.brief_id] = brief
            supabase_store.save("visit_briefs", brief, "brief_id", exclude=("signatures",))
            event_ledger.append(
                practice_id=practice_id, patient_id=patient_id,
                event_type="visit_brief_generated.v1", source_type="brief_projection",
                source_id=brief.brief_id, payload=brief.public(),
                actor_user_id=actor.user_id if actor else None,
            )
            return brief

    def get(self, brief_id: str) -> VisitBrief:
        brief = self._briefs.get(brief_id)
        if brief is None:
            raise BriefError("BRIEF_NOT_FOUND", 404)
        return brief

    def by_appointment(self, appointment_id: str) -> Optional[VisitBrief]:
        for brief in self._briefs.values():
            if brief.appointment_id == appointment_id and brief.superseded_by is None:
                return brief
        return None

    def sign(
        self,
        brief_id: str,
        *,
        actor: SessionRecord,
        attestation: str,
        expected_row_version: int,
    ) -> Signature:
        try:
            session_store.require_step_up(actor)
        except Exception as exc:
            raise BriefError("REAUTH_REQUIRED", 401, str(exc))
        if not attestation.strip():
            raise BriefError("ATTESTATION_REQUIRED", 400)
        with self._lock:
            brief = self.get(brief_id)
            if expected_row_version != brief.row_version:
                raise BriefError("STALE_BRIEF_VERSION", 409)
            if brief.signatures:
                raise BriefError("ALREADY_SIGNED", 409)
            signature = Signature(
                signature_id=str(uuid.uuid4()), brief_id=brief_id,
                signer_user_id=actor.user_id,
                signed_at=datetime.now(timezone.utc).isoformat(),
                snapshot_hash=brief.snapshot_hash,
                attestation=attestation,
                assurance=actor.assurance,
            )
            brief.signatures.append(signature)
            self._signatures[signature.signature_id] = signature
            supabase_store.save("brief_signatures", signature, "signature_id")
            event_ledger.append(
                practice_id=brief.practice_id, patient_id=brief.patient_id,
                event_type="visit_brief_signed.v1", source_type="doctor_signature",
                source_id=signature.signature_id,
                payload={"brief_id": brief_id, "snapshot_hash": brief.snapshot_hash, "attestation": attestation},
                actor_user_id=actor.user_id,
            )
            return signature

    def supersede(
        self,
        brief_id: str,
        *,
        reason: str,
        events: list[dict],
        actor: SessionRecord,
    ) -> VisitBrief:
        if not reason.strip():
            raise BriefError("SUPERSESSION_REASON_REQUIRED", 400)
        self.validate_sources(events)
        with self._lock:
            original = self.get(brief_id)
            replacement = self.generate(
                appointment_id=original.appointment_id, practice_id=original.practice_id,
                patient_id=original.patient_id, events=events, actor=actor,
            )
            replacement.row_version = original.row_version + 1
            original.superseded_by = replacement.brief_id
            supabase_store.update("visit_briefs", {"brief_id": f"eq.{brief_id}"}, {"superseded_by": replacement.brief_id})
            event_ledger.append(
                practice_id=original.practice_id, patient_id=original.patient_id,
                event_type="visit_brief_superseded.v1", source_type="doctor_supersession",
                source_id=replacement.brief_id,
                payload={"supersedes": brief_id, "reason": reason},
                actor_user_id=actor.user_id,
            )
            return replacement

    def get_signature(self, signature_id: str) -> Signature:
        signature = self._signatures.get(signature_id)
        if signature is None:
            raise BriefError("SIGNATURE_NOT_FOUND", 404)
        return signature


brief_service = BriefService()
