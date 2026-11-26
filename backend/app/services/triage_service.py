"""Human problem-report triage — handbook detailed steps 11 and 17.

 urgency is always selected by a person. The system never infers it.
 Submission atomically records the source event, creates a human triage card
 and emits an outbox message. Triage records the decision and a route preview
 derived only from approved instructions.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.services.authz_service import AuthzError
from app.services.card_state import card_service
from app.services.event_ledger import event_ledger
from app.services.session_service import SessionRecord

URGENCIES = {"routine", "priority", "urgent"}
APPROVED_INSTRUCTIONS = {
    "continue_as_directed": "Continue as directed; monitor and report changes",
    "contact_practice": "Contact the practice using the safe route",
    "urgent_review": "Attend an urgent clinical review",
}
DEADLINES = {
    "routine": "2026-11-28T17:00:00Z",
    "priority": "2026-11-26T17:00:00Z",
    "urgent": "2026-11-26T11:00:00Z",
}


@dataclass
class ProblemReport:
    report_id: str
    practice_id: str
    patient_id: str
    title: str
    description: str
    received_at: str
    status: str = "AWAITING_HUMAN_TRIAGE"
    urgency: Optional[str] = None
    approved_instruction: Optional[str] = None
    triaged_by: Optional[str] = None
    triaged_at: Optional[str] = None
    triage_card_id: Optional[str] = None
    photo_attached: bool = False


class TriageError(Exception):
    def __init__(self, code: str, status: int = 400, message: str = "") -> None:
        self.code, self.status = code, status
        self.message = message or code
        super().__init__(self.message)


class TriageService:
    def __init__(self) -> None:
        self._reports: dict[str, ProblemReport] = {}
        self._lock = threading.RLock()

    def submit(
        self,
        *,
        practice_id: str,
        patient_id: str,
        title: str,
        description: str,
        actor: Optional[SessionRecord] = None,
        photo_attached: bool = False,
    ) -> ProblemReport:
        if not title.strip() or not description.strip():
            raise TriageError("REPORT_FIELDS_REQUIRED", 400)
        with self._lock:
            report = ProblemReport(
                report_id=str(uuid.uuid4()), practice_id=practice_id, patient_id=patient_id,
                title=title, description=description,
                received_at=datetime.now(timezone.utc).isoformat(),
                photo_attached=photo_attached,
            )
            self._reports[report.report_id] = report
            event_ledger.append(
                practice_id=practice_id, patient_id=patient_id,
                event_type="problem_reported.v1", source_type="family_form",
                source_id=report.report_id,
                payload={"title": title, "description": description, "photo_attached": photo_attached},
                actor_user_id=actor.user_id if actor else None,
            )
            card = card_service.create(
                practice_id=practice_id, patient_id=patient_id,
                card_type="problem_report_triage",
                owner_membership_id="membership-orthodontist", owner_role="orthodontist",
                deadline=DEADLINES["priority"],
                actor=actor, source_id=report.report_id,
            )
            report.triage_card_id = card.card_id
            return report

    def get(self, report_id: str) -> ProblemReport:
        report = self._reports.get(report_id)
        if report is None:
            raise TriageError("REPORT_NOT_FOUND", 404)
        return report

    def triage(
        self,
        report_id: str,
        *,
        urgency: str,
        approved_instruction: str,
        actor: Optional[SessionRecord],
    ) -> dict:
        if urgency not in URGENCIES:
            raise TriageError("INVALID_URGENCY", 400)
        if approved_instruction not in APPROVED_INSTRUCTIONS:
            raise TriageError("UNAPPROVED_INSTRUCTION", 400)
        if actor is None:
            raise TriageError("HUMAN_ACTOR_REQUIRED", 403)
        with self._lock:
            report = self.get(report_id)
            if report.status != "AWAITING_HUMAN_TRIAGE":
                raise TriageError("ALREADY_TRIAGED", 409)
            report.urgency = urgency
            report.approved_instruction = approved_instruction
            report.triaged_by = actor.user_id
            report.triaged_at = datetime.now(timezone.utc).isoformat()
            report.status = "TRIAGED"
            event_ledger.append(
                practice_id=report.practice_id, patient_id=report.patient_id,
                event_type="problem_report_triaged.v1", source_type="human_triage_command",
                source_id=report.report_id,
                payload={
                    "urgency": urgency,
                    "approved_instruction": approved_instruction,
                    "triaged_by": actor.user_id,
                    "no_machine_urgency": True,
                },
                actor_user_id=actor.user_id,
            )
            started = datetime.fromisoformat(report.received_at)
            finished = datetime.fromisoformat(report.triaged_at)
            seconds = (finished - started).total_seconds()
            card = card_service.get(report.triage_card_id)
            card_service.reschedule(card.card_id, DEADLINES[urgency], actor=actor)
            return {
                "report_id": report.report_id,
                "status": report.status,
                "urgency": urgency,
                "approved_instruction": APPROVED_INSTRUCTIONS[approved_instruction],
                "route_preview": "Patient + nominated guardian · in-app first · email notice",
                "triage_latency_seconds": seconds,
                "triage_card_id": report.triage_card_id,
                "human_actor": actor.user_id,
            }


triage_service = TriageService()
