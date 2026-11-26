"""Card and loop state machine — handbook overview step 15 / detailed step 10.

Every transition is validated, versioned, audited and appended to the event
ledger. Delivery never counts as acknowledgement: only an explicit command
moves a card from OPEN to ACKNOWLEDGED.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.services.authz_service import AuthzError
from app.services.event_ledger import event_ledger
from app.services.session_service import SessionRecord

OPEN = "OPEN"
ACKNOWLEDGED = "ACKNOWLEDGED"
STARTED = "STARTED"
RESULT_RECORDED = "RESULT_RECORDED"
CLOSED = "CLOSED"
CANCELLED = "CANCELLED"

ALLOWED: dict[str, set[str]] = {
    OPEN: {ACKNOWLEDGED, CANCELLED},
    ACKNOWLEDGED: {STARTED, CANCELLED, OPEN},
    STARTED: {RESULT_RECORDED, CANCELLED},
    RESULT_RECORDED: {CLOSED},
    CLOSED: set(),
    CANCELLED: set(),
}


@dataclass
class Card:
    card_id: str
    practice_id: str
    patient_id: str
    card_type: str
    state: str
    owner_membership_id: str
    owner_role: str
    deadline: str
    row_version: int = 1
    result_code: Optional[str] = None
    cancellation_reason: Optional[str] = None
    created_at: str = ""

    def public(self) -> dict:
        return {
            "card_id": self.card_id,
            "patient_id": self.patient_id,
            "card_type": self.card_type,
            "state": self.state,
            "owner_membership_id": self.owner_membership_id,
            "owner_role": self.owner_role,
            "deadline": self.deadline,
            "row_version": self.row_version,
            "result_code": self.result_code,
            "cancellation_reason": self.cancellation_reason,
            "created_at": self.created_at,
        }


class CardStateError(Exception):
    def __init__(self, code: str, status: int = 409, message: str = "") -> None:
        self.code = code
        self.status = status
        self.message = message or code
        super().__init__(self.message)


class CardService:
    def __init__(self) -> None:
        self._cards: dict[str, Card] = {}
        self._lock = threading.RLock()

    def create(
        self,
        *,
        practice_id: str,
        patient_id: str,
        card_type: str,
        owner_membership_id: str,
        owner_role: str,
        deadline: str,
        actor: Optional[SessionRecord] = None,
        source_id: str = "rule",
    ) -> Card:
        with self._lock:
            card = Card(
                card_id=str(uuid.uuid4()),
                practice_id=practice_id,
                patient_id=patient_id,
                card_type=card_type,
                state=OPEN,
                owner_membership_id=owner_membership_id,
                owner_role=owner_role,
                deadline=deadline,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._cards[card.card_id] = card
            self._record(card, "card_created.v1", actor, source_id, {"card": card.public()})
            return card

    def get(self, card_id: str) -> Card:
        card = self._cards.get(card_id)
        if card is None:
            raise CardStateError("CARD_NOT_FOUND", 404)
        return card

    def list_for_practice(self, practice_id: str) -> list[Card]:
        return [c for c in self._cards.values() if c.practice_id == practice_id]

    def _record(self, card: Card, event_type: str, actor: Optional[SessionRecord], source_id: str, payload: dict) -> None:
        event_ledger.append(
            practice_id=card.practice_id,
            patient_id=card.patient_id,
            event_type=event_type,
            source_type="card_command",
            source_id=source_id,
            payload=payload,
            actor_user_id=actor.user_id if actor else None,
        )

    def _transition(
        self,
        card_id: str,
        target: str,
        actor: Optional[SessionRecord],
        expected_version: Optional[int],
        event_type: str,
        payload: dict,
        mutate,
    ) -> Card:
        with self._lock:
            card = self.get(card_id)
            if expected_version is not None and expected_version != card.row_version:
                raise CardStateError("STALE_ROW_VERSION", 409)
            if target not in ALLOWED[card.state]:
                raise CardStateError("FORBIDDEN_TRANSITION", 409, f"{card.state} -> {target} is not permitted")
            mutate(card)
            card.row_version += 1
            self._record(card, event_type, actor, card_id, payload)
            return card

    def acknowledge(self, card_id, actor=None, expected_version=None):
        return self._transition(
            card_id, ACKNOWLEDGED, actor, expected_version, "card_acknowledged.v1",
            {"acknowledged_by": actor.user_id if actor else None},
            lambda c: setattr(c, "state", ACKNOWLEDGED),
        )

    def start(self, card_id, actor=None, expected_version=None):
        return self._transition(
            card_id, STARTED, actor, expected_version, "card_started.v1", {},
            lambda c: setattr(c, "state", STARTED),
        )

    def result(self, card_id, result_code, actor=None, expected_version=None):
        if not result_code or not result_code.strip():
            raise CardStateError("RESULT_CODE_REQUIRED", 400)
        return self._transition(
            card_id, RESULT_RECORDED, actor, expected_version, "card_result_recorded.v1",
            {"result_code": result_code},
            lambda c: (setattr(c, "state", RESULT_RECORDED), setattr(c, "result_code", result_code)),
        )

    def close(self, card_id, actor=None, expected_version=None):
        return self._transition(
            card_id, CLOSED, actor, expected_version, "card_closed.v1", {},
            lambda c: setattr(c, "state", CLOSED),
        )

    def cancel(self, card_id, reason, actor=None, expected_version=None):
        if not reason or not reason.strip():
            raise CardStateError("CANCELLATION_REASON_REQUIRED", 400)
        return self._transition(
            card_id, CANCELLED, actor, expected_version, "card_cancelled.v1",
            {"reason": reason},
            lambda c: (setattr(c, "state", CANCELLED), setattr(c, "cancellation_reason", reason)),
        )

    def reassign(self, card_id, new_owner_membership_id, new_owner_role, actor=None, expected_version=None):
        with self._lock:
            card = self.get(card_id)
            if expected_version is not None and expected_version != card.row_version:
                raise CardStateError("STALE_ROW_VERSION", 409)
            if card.state in {CLOSED, CANCELLED}:
                raise CardStateError("FORBIDDEN_TRANSITION", 409)
            card.owner_membership_id = new_owner_membership_id
            card.owner_role = new_owner_role
            card.row_version += 1
            self._record(card, "card_reassigned.v1", actor, card_id, {"owner": new_owner_membership_id})
            return card

    def reschedule(self, card_id, new_deadline, actor=None, expected_version=None):
        with self._lock:
            card = self.get(card_id)
            if expected_version is not None and expected_version != card.row_version:
                raise CardStateError("STALE_ROW_VERSION", 409)
            if card.state in {CLOSED, CANCELLED}:
                raise CardStateError("FORBIDDEN_TRANSITION", 409)
            card.deadline = new_deadline
            card.row_version += 1
            self._record(card, "card_rescheduled.v1", actor, card_id, {"deadline": new_deadline})
            return card


card_service = CardService()
