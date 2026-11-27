"""Assistant chair capture and front-desk booking/promise operations.

Handbook detailed steps 16 and 18 (chair card and front desk). Chair capture
is pinned to an exact appointment and approved checklist version; promises
resolve relative deadlines to absolute timestamps and create one event per
business effect.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.authz_service import AuthzError
from app.services.event_ledger import event_ledger
from app.services.session_service import SessionRecord
from app.services import supabase_store

CHECKLIST_VERSION = "chair-v3"


class OperationsError(Exception):
    def __init__(self, code: str, status: int = 400, message: str = "") -> None:
        self.code, self.status = code, status
        self.message = message or code
        super().__init__(self.message)


@dataclass
class Appointment:
    appointment_id: str
    practice_id: str
    patient_id: str
    scheduled_at: str
    reason: str
    status: str = "confirmed"
    clinician: str = "orthodontist"


@dataclass
class Promise:
    promise_id: str
    practice_id: str
    patient_id: str
    text: str
    owner_membership_id: str
    due_at: str
    state: str = "open"


@dataclass
class ChairCapture:
    capture_id: str
    appointment_id: str
    patient_id: str
    capture_type: str
    content: str
    checklist_version: str
    captured_by: str
    captured_at: str


class OperationsService:
    def __init__(self) -> None:
        self._appointments: dict[str, Appointment] = {}
        self._promises: dict[str, Promise] = {}
        self._captures: dict[str, ChairCapture] = {}
        self._lock = threading.RLock()

    def seed_appointment(self, practice_id="wzdm-01", patient_id="p-600", appointment_id="apt-600") -> Appointment:
        with self._lock:
            if appointment_id not in self._appointments:
                self._appointments[appointment_id] = Appointment(
                    appointment_id=appointment_id, practice_id=practice_id,
                    patient_id=patient_id, scheduled_at="2026-11-27T10:30:00Z",
                    reason="Adjustment",
                )
            return self._appointments[appointment_id]

    def appointment(self, appointment_id: str) -> Appointment:
        self.seed_appointment(appointment_id=appointment_id)
        return self._appointments[appointment_id]

    def chair_card(self, appointment_id: str) -> dict:
        appointment = self.appointment(appointment_id)
        return {
            "appointment_id": appointment.appointment_id,
            "patient_id": appointment.patient_id,
            "scheduled_at": appointment.scheduled_at,
            "reason": appointment.reason,
            "checklist_version": CHECKLIST_VERSION,
            "context_confirmation_required": True,
            "captured": [c.public() for c in self._captures.values() if c.appointment_id == appointment_id],
        }

    def capture(
        self,
        appointment_id: str,
        patient_id: str,
        capture_type: str,
        content: str,
        actor: SessionRecord,
        checklist_version: str,
    ) -> ChairCapture:
        appointment = self.appointment(appointment_id)
        if appointment.patient_id != patient_id:
            raise OperationsError("PATIENT_CONTEXT_MISMATCH", 409)
        if checklist_version != CHECKLIST_VERSION:
            raise OperationsError("STALE_CHECKLIST_VERSION", 409)
        if capture_type not in {"clinical_observation", "photo", "patient_statement"}:
            raise OperationsError("INVALID_CAPTURE_TYPE", 400)
        if not content.strip():
            raise OperationsError("CAPTURE_CONTENT_REQUIRED", 400)
        with self._lock:
            capture = ChairCapture(
                capture_id=str(uuid.uuid4()), appointment_id=appointment_id,
                patient_id=patient_id, capture_type=capture_type, content=content,
                checklist_version=checklist_version, captured_by=actor.user_id,
                captured_at=datetime.now(timezone.utc).isoformat(),
            )
            self._captures[capture.capture_id] = capture
            supabase_store.save("chairside_captures", capture, "capture_id")
            event_ledger.append(
                practice_id=appointment.practice_id, patient_id=patient_id,
                event_type="chairside_capture_recorded.v1", source_type="chair_capture",
                source_id=capture.capture_id, payload=capture.__dict__,
                actor_user_id=actor.user_id,
            )
            return capture

    @staticmethod
    def resolve_due(phrase: str, now: Optional[datetime] = None) -> str:
        now = now or datetime.now(timezone.utc)
        mapping = {
            "today": now.replace(hour=17, minute=0, second=0, microsecond=0),
            "tomorrow": (now + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0),
            "next business day": (now + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0),
        }
        key = phrase.strip().lower()
        if key not in mapping:
            raise OperationsError("UNRESOLVED_DEADLINE", 400)
        return mapping[key].isoformat()

    def make_promise(
        self, practice_id: str, patient_id: str, text: str, owner_membership_id: str,
        due_phrase: str, actor: SessionRecord,
    ) -> Promise:
        if not text.strip():
            raise OperationsError("PROMISE_TEXT_REQUIRED", 400)
        due_at = self.resolve_due(due_phrase)
        with self._lock:
            promise = Promise(
                promise_id=str(uuid.uuid4()), practice_id=practice_id, patient_id=patient_id,
                text=text, owner_membership_id=owner_membership_id, due_at=due_at,
            )
            self._promises[promise.promise_id] = promise
            supabase_store.save("promises", promise, "promise_id")
            event_ledger.append(
                practice_id=practice_id, patient_id=patient_id,
                event_type="promise_made.v1", source_type="front_desk",
                source_id=promise.promise_id, payload=promise.__dict__,
                actor_user_id=actor.user_id,
            )
            return promise

    def promises(self, practice_id: str) -> list[Promise]:
        return [p for p in self._promises.values() if p.practice_id == practice_id]

    def promise(self, promise_id: str) -> Promise:
        promise = self._promises.get(promise_id)
        if promise is None:
            raise OperationsError("PROMISE_NOT_FOUND", 404)
        return promise


operations_service = OperationsService()

# Add public() to ChairCapture for route serialization
ChairCapture.public = lambda self: {
    "capture_id": self.capture_id,
    "appointment_id": self.appointment_id,
    "patient_id": self.patient_id,
    "capture_type": self.capture_type,
    "checklist_version": self.checklist_version,
    "captured_by": self.captured_by,
    "captured_at": self.captured_at,
}
