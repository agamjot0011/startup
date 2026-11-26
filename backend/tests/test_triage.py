"""Human triage tests — no inferred urgency, approved instructions only."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.card_state import card_service
from app.services.event_ledger import event_ledger
from app.services.session_service import session_store
from app.services.triage_service import TriageError, triage_service

client = TestClient(app)


def _session(role, patient="p-400"):
    s = session_store.create(
        user_id=f"triage-{role}",
        assurance="high", auth_methods=["oidc", "mfa"],
        practice_id="wzdm-01", membership_id=f"membership-{role}",
        roles=[role],
    )
    s.patient_id = patient
    return s


def _headers(s):
    return {"Authorization": f"Bearer {s.session_id}"}


def test_submission_creates_event_and_human_triage_card():
    actor = _session("patient")
    before = len(event_ledger._order)
    report = triage_service.submit(
        practice_id="wzdm-01", patient_id="p-400",
        title="Loose bracket", description="Upper left since yesterday",
        actor=actor,
    )
    assert report.status == "AWAITING_HUMAN_TRIAGE"
    assert report.urgency is None
    assert report.triage_card_id
    assert card_service.get(report.triage_card_id).state == "OPEN"
    new_events = event_ledger._order[before:]
    assert event_ledger._events[new_events[0]].event_type == "problem_reported.v1"
    assert event_ledger._events[new_events[1]].event_type == "card_created.v1"
    assert len(new_events) == 2


def test_triage_requires_human_and_approved_values():
    report = triage_service.submit(
        practice_id="wzdm-01", patient_id="p-401", title="t", description="d"
    )
    with pytest.raises(TriageError) as exc:
        triage_service.triage(report.report_id, urgency="urgent",
                              approved_instruction="urgent_review", actor=None)
    assert exc.value.code == "HUMAN_ACTOR_REQUIRED"

    dentist = _session("orthodontist")
    with pytest.raises(TriageError) as exc:
        triage_service.triage(report.report_id, urgency="guessed",
                              approved_instruction="urgent_review", actor=dentist)
    assert exc.value.code == "INVALID_URGENCY"

    with pytest.raises(TriageError) as exc:
        triage_service.triage(report.report_id, urgency="urgent",
                              approved_instruction="write_your_own", actor=dentist)
    assert exc.value.code == "UNAPPROVED_INSTRUCTION"


def test_triage_records_decision_latency_and_reschedules_card():
    report = triage_service.submit(
        practice_id="wzdm-01", patient_id="p-402", title="t", description="d"
    )
    dentist = _session("orthodontist")
    result = triage_service.triage(
        report.report_id, urgency="priority", approved_instruction="contact_practice", actor=dentist
    )
    assert result["status"] == "TRIAGED"
    assert result["urgency"] == "priority"
    assert result["human_actor"] == dentist.user_id
    assert result["triage_latency_seconds"] >= 0
    assert "machine" not in result
    assert card_service.get(report.triage_card_id).deadline == "2026-11-26T17:00:00Z"

    with pytest.raises(TriageError) as exc:
        triage_service.triage(report.report_id, urgency="urgent",
                              approved_instruction="urgent_review", actor=dentist)
    assert exc.value.code == "ALREADY_TRIAGED"


def test_api_submit_and_triage_enforce_roles():
    patient = _session("patient", patient="p-403")
    submit = client.post(
        "/v1/reports/p-403/reports",
        json={"title": "Pain", "description": "On chewing"},
        headers=_headers(patient),
    )
    assert submit.status_code == 200
    report_id = submit.json()["report_id"]

    assistant = _session("clinical_assistant")
    denied = client.post(
        f"/v1/problem-reports/{report_id}/triage",
        json={"urgency": "urgent", "approved_instruction": "urgent_review"},
        headers=_headers(assistant),
    )
    assert denied.status_code == 403

    dentist = _session("orthodontist")
    ok = client.post(
        f"/v1/problem-reports/{report_id}/triage",
        json={"urgency": "urgent", "approved_instruction": "urgent_review"},
        headers=_headers(dentist),
    )
    assert ok.status_code == 200
    assert ok.json()["urgency"] == "urgent"
