"""Assistant chair capture and front-desk promise tests."""

from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.services.event_ledger import event_ledger
from app.services.operations_service import (
    CHECKLIST_VERSION,
    OperationsError,
    operations_service,
)
from app.services.session_service import session_store

client = TestClient(app)


def _session(role, user=None):
    return session_store.create(
        user_id=user or f"ops-{role}", assurance="high", auth_methods=["oidc", "mfa"],
        practice_id="wzdm-01", membership_id=f"membership-{role}", roles=[role],
    )


def _headers(s):
    return {"Authorization": f"Bearer {s.session_id}"}


def test_chair_card_pins_appointment_and_checklist():
    card = operations_service.chair_card("apt-700")
    assert card["checklist_version"] == CHECKLIST_VERSION
    assert card["context_confirmation_required"] is True
    assert card["patient_id"] == "p-600"


def test_capture_enforces_context_and_checklist():
    assistant = _session("clinical_assistant", "capture-assistant")
    appointment = operations_service.seed_appointment(appointment_id="apt-701", patient_id="p-701")

    try:
        operations_service.capture("apt-701", "p-999", "photo", "x", assistant, CHECKLIST_VERSION)
    except OperationsError as exc:
        assert exc.code == "PATIENT_CONTEXT_MISMATCH"
    else:
        raise AssertionError("expected context mismatch")

    try:
        operations_service.capture("apt-701", "p-701", "photo", "x", assistant, "chair-v2")
    except OperationsError as exc:
        assert exc.code == "STALE_CHECKLIST_VERSION"
    else:
        raise AssertionError("expected stale checklist")

    before = len(event_ledger._order)
    capture = operations_service.capture(
        "apt-701", "p-701", "clinical_observation", "Bond intact", assistant, CHECKLIST_VERSION
    )
    assert capture.captured_by == "capture-assistant"
    assert event_ledger._events[event_ledger._order[-1]].event_type == "chairside_capture_recorded.v1"
    assert len(event_ledger._order) == before + 1


def test_promise_deadline_resolves_to_absolute():
    now = datetime(2026, 11, 26, 9, 0, tzinfo=timezone.utc)
    assert operations_service.resolve_due("today", now) == "2026-11-26T17:00:00+00:00"
    assert operations_service.resolve_due("tomorrow", now) == "2026-11-27T17:00:00+00:00"
    try:
        operations_service.resolve_due("whenever", now)
    except OperationsError as exc:
        assert exc.code == "UNRESOLVED_DEADLINE"
    else:
        raise AssertionError("expected unresolved deadline")


def test_promise_creation_writes_event():
    front_desk = _session("front_desk", "promise-owner")
    before = len(event_ledger._order)
    promise = operations_service.make_promise(
        "wzdm-01", "p-702", "Call back about retainer cost",
        "membership-front-desk", "tomorrow", front_desk,
    )
    assert "T17:00:00" in promise.due_at
    assert event_ledger._events[event_ledger._order[-1]].event_type == "promise_made.v1"
    assert len(event_ledger._order) == before + 1


def test_api_enforces_role_boundaries():
    assistant = _session("clinical_assistant", "api-assistant")
    dentist = _session("orthodontist", "api-dentist")
    operations_service.seed_appointment(appointment_id="apt-710", patient_id="p-710")

    denied = client.post(
        "/v1/patients/p-710/promises",
        json={"text": "call", "owner_membership_id": "m", "due_phrase": "today"},
        headers=_headers(dentist),
    )
    assert denied.status_code == 403

    front_desk = _session("front_desk", "api-front-desk")
    ok = client.post(
        "/v1/patients/p-710/promises",
        json={"text": "call back", "owner_membership_id": "m", "due_phrase": "tomorrow"},
        headers=_headers(front_desk),
    )
    assert ok.status_code == 200

    capture = client.post(
        "/v1/patients/p-710/chairside-captures",
        json={
            "appointment_id": "apt-710", "capture_type": "photo",
            "content": "Frontal view", "checklist_version": CHECKLIST_VERSION,
        },
        headers=_headers(assistant),
    )
    assert capture.status_code == 200
    assert capture.json()["capture_type"] == "photo"
