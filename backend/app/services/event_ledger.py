"""Append-only care event ledger, transactional outbox and idempotency.

Handbook overview step 11 (lines 1135-1140), step 9 done criteria
(lines 4813-4821), and step 21.1 (line 8284).

Events are never updated or deleted. Corrections append a new event that
references the original. Each event is chained by SHA-256 over its canonical
payload plus the previous hash, so tampering is detectable by re-computation.
The in-memory store is alpha scaffolding; production uses the database with
RLS and a real outbox worker.
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from app.services.authz_service import AuthzError


@dataclass
class CareEvent:
    event_id: str
    practice_id: str
    patient_id: str
    event_type: str
    source_type: str
    source_id: str
    payload: dict
    actor_user_id: Optional[str]
    recorded_at: str
    prev_hash: str
    event_hash: str
    correction_of: Optional[str] = None
    correction_reason: Optional[str] = None
    superseded_by: Optional[str] = None


@dataclass
class OutboxMessage:
    outbox_id: str
    practice_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict
    status: str = "pending"
    attempts: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dispatched_at: Optional[str] = None


@dataclass
class IdempotencyRecord:
    scope: str
    key: str
    request_hash: str
    status: str
    response: Optional[dict] = None


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class EventLedger:
    def __init__(self) -> None:
        self._events: dict[str, CareEvent] = {}
        self._order: list[str] = []
        self._outbox: list[OutboxMessage] = []
        self._idempotency: dict[tuple[str, str], IdempotencyRecord] = {}
        self._lock = threading.RLock()
        self._head_hash = "0" * 64

    def append(
        self,
        *,
        practice_id: str,
        patient_id: str,
        event_type: str,
        source_type: str,
        source_id: str,
        payload: dict,
        actor_user_id: Optional[str] = None,
        correction_of: Optional[str] = None,
        correction_reason: Optional[str] = None,
        enqueue: bool = True,
    ) -> CareEvent:
        with self._lock:
            if correction_of and correction_of not in self._events:
                raise AuthzError("UNKNOWN_SOURCE_EVENT", 404)
            event_id = str(uuid.uuid4())
            recorded_at = datetime.now(timezone.utc).isoformat()
            body = {
                "event_id": event_id,
                "practice_id": practice_id,
                "patient_id": patient_id,
                "event_type": event_type,
                "source_type": source_type,
                "source_id": source_id,
                "payload": payload,
                "actor_user_id": actor_user_id,
                "recorded_at": recorded_at,
                "correction_of": correction_of,
                "correction_reason": correction_reason,
            }
            prev_hash = self._head_hash
            event_hash = hashlib.sha256((prev_hash + _canonical(body)).encode("utf-8")).hexdigest()
            event = CareEvent(
                event_id=event_id, practice_id=practice_id, patient_id=patient_id,
                event_type=event_type, source_type=source_type, source_id=source_id,
                payload=payload, actor_user_id=actor_user_id, recorded_at=recorded_at,
                prev_hash=prev_hash, event_hash=event_hash,
                correction_of=correction_of, correction_reason=correction_reason,
            )
            self._events[event_id] = event
            self._order.append(event_id)
            self._head_hash = event_hash
            if correction_of:
                self._events[correction_of].superseded_by = event_id
            if enqueue:
                self._outbox.append(OutboxMessage(
                    outbox_id=str(uuid.uuid4()), practice_id=practice_id,
                    event_type=event_type, aggregate_type="patient", aggregate_id=patient_id,
                    payload=body,
                ))
            return event

    def correct(self, event_id: str, *, payload: dict, reason: str, actor_user_id: Optional[str]) -> CareEvent:
        original = self.get(event_id)
        return self.append(
            practice_id=original.practice_id,
            patient_id=original.patient_id,
            event_type=original.event_type + ".corrected",
            source_type="correction",
            source_id=event_id,
            payload=payload,
            actor_user_id=actor_user_id,
            correction_of=event_id,
            correction_reason=reason,
        )

    def get(self, event_id: str) -> CareEvent:
        event = self._events.get(event_id)
        if event is None:
            raise AuthzError("EVENT_NOT_FOUND", 404)
        return event

    def timeline(self, practice_id: str, patient_id: str) -> list[dict]:
        return [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "patient_id": e.patient_id,
                "source_type": e.source_type,
                "source_id": e.source_id,
                "recorded_at": e.recorded_at,
                "actor_user_id": e.actor_user_id,
                "correction_of": e.correction_of,
                "superseded_by": e.superseded_by,
                "event_hash": e.event_hash,
            }
            for e in self._events.values()
            if e.practice_id == practice_id and e.patient_id == patient_id
        ]

    def reconstruct(self, event_id: str) -> dict:
        event = self.get(event_id)
        chain = []
        current = event
        while current.correction_of:
            chain.append(current)
            current = self._events[current.correction_of]
        chain.append(current)
        chain.reverse()
        return {
            "original_event_id": current.event_id,
            "corrections": [e.event_id for e in chain[1:]],
            "events": [{"event_id": e.event_id, "payload": e.payload, "reason": e.correction_reason} for e in chain],
            "verified": self.verify(),
        }

    def verify(self) -> bool:
        with self._lock:
            prev = "0" * 64
            for event_id in self._order:
                e = self._events[event_id]
                body = {
                    "event_id": e.event_id, "practice_id": e.practice_id,
                    "patient_id": e.patient_id, "event_type": e.event_type,
                    "source_type": e.source_type, "source_id": e.source_id,
                    "payload": e.payload, "actor_user_id": e.actor_user_id,
                    "recorded_at": e.recorded_at, "correction_of": e.correction_of,
                    "correction_reason": e.correction_reason,
                }
                expected = hashlib.sha256((prev + _canonical(body)).encode("utf-8")).hexdigest()
                if expected != e.event_hash or e.prev_hash != prev:
                    return False
                prev = e.event_hash
            return prev == self._head_hash

    # ---- outbox ----
    def pending_outbox(self) -> list[OutboxMessage]:
        with self._lock:
            return [m for m in self._outbox if m.status == "pending"]

    def dispatch_outbox(self, limit: int = 100) -> int:
        with self._lock:
            count = 0
            for message in self._outbox:
                if message.status == "pending" and count < limit:
                    message.status = "dispatched"
                    message.attempts += 1
                    message.dispatched_at = datetime.now(timezone.utc).isoformat()
                    count += 1
            return count

    # ---- idempotency ----
    def execute_idempotent(
        self, scope: str, key: str, request: dict, fn: Callable[[], dict]
    ) -> tuple[dict, bool]:
        request_hash = hashlib.sha256(_canonical(request).encode("utf-8")).hexdigest()
        with self._lock:
            existing = self._idempotency.get((scope, key))
            if existing:
                if existing.request_hash != request_hash:
                    raise AuthzError("IDEMPOTENCY_KEY_REUSE", 409)
                return existing.response or {}, True
            response = fn()
            self._idempotency[(scope, key)] = IdempotencyRecord(
                scope=scope, key=key, request_hash=request_hash, status="completed", response=response
            )
            return response, False


event_ledger = EventLedger()
