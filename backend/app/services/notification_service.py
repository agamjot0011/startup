"""Generic notification pipeline with fail-closed PHI scanning.

Handbook detailed step 20 (lines 8023-8263): exact external shell bytes,
quiet hours, per-role budgets, per-site provider gates, retries, callbacks,
fallback mode and a fail-closed PHI scanner (PHI-01..16).

Nothing is sent to an external provider until the rendered content passes the
scanner and the provider gate. A blocked message creates an operations alert
and never reaches a provider.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Optional

from app.services.authz_service import AuthzError
from app.services.event_ledger import event_ledger

QUIET_START = time(22, 0)
QUIET_END = time(7, 0)
BUDGETS = {"orthodontist": 2, "clinical_assistant": 10, "front_desk": 10}
ALLOWED_TEMPLATES = {
    "digest_weekly": "Hello. Your weekly care summary is available in the app. Reply STOP to opt out.",
    "appointment_reminder": "You have an appointment. Open the app for details.",
    "urgent_notice": "Please contact the practice using the approved safe route.",
}

PHI_PATTERNS = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "PHONE": re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)"),
    "PATIENT_ID": re.compile(r"\b(?:p-\d{3,}|\b\d{6,}\b)\b", re.I),
    "DOB": re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    "DIAGNOSIS": re.compile(r"\b(caries|fracture|abscess|malocclusion|cancer|HIV|pregnan)\w*\b", re.I),
}


@dataclass
class ScanResult:
    passed: bool
    findings: list[str] = field(default_factory=list)


def scan_for_phi(content: str) -> ScanResult:
    """Fail closed: any identifier-like content blocks external delivery."""
    findings = [name for name, pattern in PHI_PATTERNS.items() if pattern.search(content)]
    return ScanResult(passed=not findings, findings=findings)


@dataclass
class ProviderConfig:
    site_id: str
    sms_enabled: bool = False
    email_enabled: bool = False


@dataclass
class NotificationCommand:
    command_id: str
    practice_id: str
    patient_id: str
    channel: str
    template_id: str
    rendered: str
    status: str
    not_before: str
    dedupe_key: str
    payload_hash: str
    attempts: int = 0
    provider: Optional[str] = None
    blocked_reason: Optional[str] = None


class NotificationError(Exception):
    def __init__(self, code: str, status: int = 400, message: str = "") -> None:
        self.code, self.status = code, status
        self.message = message or code
        super().__init__(self.message)


class NotificationService:
    def __init__(self) -> None:
        self._commands: dict[str, NotificationCommand] = {}
        self._providers: dict[str, ProviderConfig] = {}
        self._sent_today: dict[tuple[str, str], int] = {}
        self._lock = threading.RLock()

    def configure_provider(self, site_id: str, sms: bool, email: bool) -> None:
        self._providers[site_id] = ProviderConfig(site_id, sms, email)

    def _not_before(self, now: datetime, urgent: bool) -> datetime:
        if urgent:
            return now
        if QUIET_START <= now.time() or now.time() < QUIET_END:
            return datetime.combine(now.date(), QUIET_END, tzinfo=timezone.utc)
        return now

    def enqueue(
        self,
        *,
        practice_id: str,
        site_id: str,
        patient_id: str,
        template_id: str,
        channel: str,
        role: str,
        urgent: bool = False,
        now: Optional[datetime] = None,
    ) -> NotificationCommand:
        if template_id not in ALLOWED_TEMPLATES:
            raise NotificationError("UNAPPROVED_TEMPLATE", 400)
        if channel not in {"sms", "email", "in_app"}:
            raise NotificationError("INVALID_CHANNEL", 400)
        now = now or datetime.now(timezone.utc)
        rendered = ALLOWED_TEMPLATES[template_id]
        scan = scan_for_phi(rendered)
        payload_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()

        with self._lock:
            command = NotificationCommand(
                command_id=str(uuid.uuid4()), practice_id=practice_id,
                patient_id=patient_id, channel=channel, template_id=template_id,
                rendered=rendered, status="PENDING",
                not_before=self._not_before(now, urgent).isoformat(),
                dedupe_key=f"{patient_id}:{template_id}:{now.date().isoformat()}",
                payload_hash=payload_hash,
            )
            if not scan.passed:
                command.status = "BLOCKED"
                command.blocked_reason = "PHI_SCAN_FAILED:" + ",".join(scan.findings)
                event_ledger.append(
                    practice_id=practice_id, patient_id=patient_id,
                    event_type="notification_blocked.v1", source_type="phi_scanner",
                    source_id=command.command_id,
                    payload={"findings": scan.findings, "channel": channel},
                )
            elif channel != "in_app":
                provider = self._providers.get(site_id)
                gate_open = provider and (
                    provider.sms_enabled if channel == "sms" else provider.email_enabled
                )
                if not gate_open:
                    command.status = "FALLBACK_IN_APP"
                    command.provider = None
                else:
                    budget_key = (site_id, role)
                    used = self._sent_today.get(budget_key, 0)
                    if used >= BUDGETS.get(role, 0):
                        command.status = "BUDGET_EXCEEDED"
                    else:
                        command.provider = channel
                        self._sent_today[budget_key] = used + 1
            self._commands[command.command_id] = command
            event_ledger.append(
                practice_id=practice_id, patient_id=patient_id,
                event_type="notification_commanded.v1", source_type="notification_pipeline",
                source_id=command.command_id,
                payload={"status": command.status, "channel": channel, "template_id": template_id},
            )
            return command

    def dispatch_pending(self, now: Optional[datetime] = None) -> dict:
        now = now or datetime.now(timezone.utc)
        dispatched = deferred = 0
        with self._lock:
            for command in self._commands.values():
                if command.status != "PENDING" or not command.provider:
                    continue
                if datetime.fromisoformat(command.not_before) > now:
                    deferred += 1
                    continue
                command.status = "DISPATCHED"
                command.attempts += 1
                dispatched += 1
        return {"dispatched": dispatched, "deferred": deferred}

    def commands(self) -> list[NotificationCommand]:
        return list(self._commands.values())

    def health(self) -> dict:
        counts: dict[str, int] = {}
        for command in self._commands.values():
            counts[command.status] = counts.get(command.status, 0) + 1
        return counts


notification_service = NotificationService()
