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
from app.services import supabase_store


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
        self._loaded = False

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            rows = supabase_store.select("care_events", order="recorded_at.asc", limit=5000)
            for row in rows:
                payload = row.get("payload") or {}
                if isinstance(payload, str):
                    payload = json.loads(payload)
                event = CareEvent(
                    event_id=row["event_id"], practice_id=row["practice_id"],
                    patient_id=row["patient_id"], event_type=row["event_type"],
                    source_type=row["source_type"], source_id=row["source_id"],
                    payload=payload,
                    actor_user_id=row.get("actor_user_id"), recorded_at=row["recorded_at"],
                    prev_hash=row["prev_hash"], event_hash=row["event_hash"],
                    correction_of=row.get("correction_of"),
                    correction_reason=row.get("correction_reason"),
                    superseded_by=row.get("superseded_by"),
                )
                if event.event_id in self._events:
                    continue
                self._events[event.event_id] = event
                self._order.append(event.event_id)
            if self._order:
                self._head_hash = self._events[self._order[-1]].event_hash
            self._loaded = True
            for row in supabase_store.select("idempotency_records", limit=5000):
                key = row.get("idempotency_key", "")
                if ":" not in key:
                    continue
                scope, idem_key = key.split(":", 1)
                self._idempotency[(scope, idem_key)] = IdempotencyRecord(
                    scope=scope, key=idem_key,
                    request_hash=row.get("request_hash") or "",
                    status="completed", response=row.get("response_body"),
                )

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
            self._load()
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
            supabase_store.upsert("care_events", {
                "event_id": event.event_id, "practice_id": event.practice_id,
                "patient_id": event.patient_id, "event_type": event.event_type,
                "source_type": event.source_type, "source_id": event.source_id,
                "payload": event.payload, "actor_user_id": event.actor_user_id,
                "recorded_at": event.recorded_at, "prev_hash": event.prev_hash,
                "event_hash": event.event_hash, "correction_of": event.correction_of,
                "correction_reason": event.correction_reason, "superseded_by": event.superseded_by,
            }, "event_id")
            if correction_of:
                self._events[correction_of].superseded_by = event_id
                supabase_store.update("care_events", {"event_id": f"eq.{correction_of}"}, {"superseded_by": event_id})
            if enqueue:
                message = OutboxMessage(
                    outbox_id=str(uuid.uuid4()), practice_id=practice_id,
                    event_type=event_type, aggregate_type="patient", aggregate_id=patient_id,
                    payload=body,
                )
                self._outbox.append(message)
                supabase_store.insert("outbox_messages", {
                    "id": supabase_store.uid(message.outbox_id),
                    "practice_id": supabase_store.uid(practice_id or "wzdm-01"),
                    "event_type": event_type,
                    "aggregate_type": "patient",
                    "payload": body,
                    "status": "pending",
                    "attempts": 0,
                    "created_at": message.created_at,
                })
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
        self._load()
        event = self._events.get(event_id)
        if event is None:
            raise AuthzError("EVENT_NOT_FOUND", 404)
        return event

    def timeline(self, practice_id: str, patient_id: str) -> list[dict]:
        self._load()
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
        self._load()
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
                    supabase_store.update("outbox_messages", {"id": f"eq.{supabase_store.uid(message.outbox_id)}"}, {
                        "status": "dispatched", "attempts": message.attempts,
                        "dispatched_at": message.dispatched_at,
                    })
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
            record = IdempotencyRecord(
                scope=scope, key=key, request_hash=request_hash, status="completed", response=response
            )
            self._idempotency[(scope, key)] = record
            supabase_store.insert("idempotency_records", {
                "id": supabase_store.uid(f"{scope}:{key}"),
                "practice_id": supabase_store.uid("wzdm-01"),
                "idempotency_key": f"{scope}:{key}",
                "request_hash": request_hash,
                "response_status": 200,
                "response_body": response,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            return response, False


event_ledger = EventLedger()
