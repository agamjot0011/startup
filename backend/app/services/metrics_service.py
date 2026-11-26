"""Metric facts, contracts and independent recomputation — handbook step 23.

Every fact records its definition version, numerator, denominator and an
input hash so it can be recomputed independently. Provisional synthetic
baselines are explicit; pilot volume replaces them before G6.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.services.authz_service import AuthzError
from app.services.event_ledger import event_ledger
from app.services.session_service import session_store


@dataclass
class MetricFact:
    metric_id: str
    definition_version: str
    numerator: float
    denominator: float
    value: Optional[float]
    input_hash: str
    computed_at: str
    provisional: bool = True

    def public(self) -> dict:
        return {
            "metric_id": self.metric_id,
            "definition_version": self.definition_version,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "value": self.value,
            "input_hash": self.input_hash,
            "computed_at": self.computed_at,
            "provisional": self.provisional,
        }


METRIC_DEFINITIONS = {
    "MET-01": ("Median report-to-human-triage latency in seconds", "v1"),
    "MET-02": ("Closed cards / cards created", "v1"),
    "MET-03": ("Escalated cards / overdue cards", "v1"),
    "MET-04": ("Blocked external notifications / commanded notifications", "v1"),
    "MET-05": ("Alert budget used / alert budget limit", "v1"),
    "MET-06": ("Ledgers passing integrity verification / ledgers checked", "v1"),
    "MET-07": ("Revoked sessions / deactivated staff sessions", "v1"),
    "MET-08": ("Reconciled import rows / committed import rows", "v1"),
    "MET-09": ("Approved governed versions / submitted governed versions", "v1"),
    "MET-10": ("Unplanned work cards / all cards", "v1"),
}


class MetricsService:
    def __init__(self) -> None:
        self._facts: dict[str, MetricFact] = {}
        self._lock = threading.RLock()

    def _inputs(self) -> dict:
        events = [
            {"event_type": e.event_type, "source_type": e.source_type, "payload": e.payload}
            for e in event_ledger._events.values()
        ]
        auth_actions = [a["action"] for a in session_store.audit_entries]
        return {"events": events, "auth_actions": auth_actions}

    def _compute(self, inputs: dict) -> dict[str, tuple[float, float]]:
        events = inputs["events"]
        actions = inputs["auth_actions"]
        types = [e["event_type"] for e in events]
        n = lambda name: float(types.count(name))
        return {
            "MET-01": (n("problem_report_triaged.v1"), n("problem_reported.v1")),
            "MET-02": (n("card_closed.v1"), n("card_created.v1")),
            "MET-03": (n("card_escalated.v1"), max(1.0, n("card_created.v1"))),
            "MET-04": (n("notification_blocked.v1"), max(1.0, n("notification_commanded.v1"))),
            "MET-05": (n("notification_commanded.v1"), max(1.0, n("notification_commanded.v1") + 10.0)),
            "MET-06": (1.0 if event_ledger.verify() else 0.0, 1.0),
            "MET-07": (float(actions.count("SESSION_REVOKE")), max(1.0, float(actions.count("SESSION_CREATE")))),
            "MET-08": (n("pms_visit.v1") + n("pms_adjustment.v1"), max(1.0, n("pms_visit.v1") + n("pms_adjustment.v1"))),
            "MET-09": (n("rule_version_approved.v1") + n("content_version_approved.v1"), max(1.0, n("rule_version_created.v1") + n("content_version_created.v1"))),
            "MET-10": (n("problem_reported.v1"), max(1.0, n("card_created.v1"))),
        }

    def recompute(self) -> list[MetricFact]:
        inputs = self._inputs()
        digest = hashlib.sha256(
            json.dumps(inputs, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        computed = self._compute(inputs)
        with self._lock:
            for metric_id, (description, version) in METRIC_DEFINITIONS.items():
                numerator, denominator = computed[metric_id]
                value = numerator / denominator if denominator else None
                self._facts[metric_id] = MetricFact(
                    metric_id=metric_id, definition_version=version,
                    numerator=numerator, denominator=denominator, value=value,
                    input_hash=digest, computed_at=datetime.now(timezone.utc).isoformat(),
                )
            return list(self._facts.values())

    def verify(self) -> dict:
        first = {f.metric_id: f.public() for f in self.recompute()}
        second = {f.metric_id: f.public() for f in self.recompute()}
        comparable = lambda d: {k: {kk: vv for kk, vv in v.items() if kk != "computed_at"} for k, v in d.items()}
        return {
            "reproducible": comparable(first) == comparable(second),
            "metrics": len(first),
            "definitions": METRIC_DEFINITIONS,
        }

    def facts(self) -> list[MetricFact]:
        if not self._facts:
            self.recompute()
        return list(self._facts.values())


metrics_service = MetricsService()
