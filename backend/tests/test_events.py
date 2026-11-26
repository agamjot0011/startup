"""Append-only event ledger, corrections, outbox and idempotency tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.authz_service import AuthzError
from app.services.event_ledger import event_ledger
from app.services.session_service import session_store

client = TestClient(app)


def _session(role="orthodontist", practice="wzdm-01"):
    return session_store.create(
        user_id=f"event-user-{role}",
        assurance="high",
        auth_methods=["oidc", "mfa"],
        practice_id=practice,
        membership_id=f"membership-{practice}",
        roles=[role],
    )


def _headers(session):
    return {"Authorization": f"Bearer {session.session_id}"}


def test_events_are_hash_chained_and_immutable():
    before = len(event_ledger._order)
    first = event_ledger.append(
        practice_id="wzdm-01", patient_id="p-100", event_type="visit.v1",
        source_type="pms", source_id="src-1", payload={"note": "original"},
        actor_user_id="actor-1",
    )
    second = event_ledger.append(
        practice_id="wzdm-01", patient_id="p-100", event_type="card.v1",
        source_type="staff", source_id="src-2", payload={"note": "next"},
        actor_user_id="actor-1",
    )
    assert second.prev_hash == first.event_hash
    assert event_ledger.verify() is True
    assert len(event_ledger._order) == before + 2

    # Direct mutation is detectable by hash recomputation.
    first.payload["note"] = "tampered"
    assert event_ledger.verify() is False
    first.payload["note"] = "original"
    assert event_ledger.verify() is True


def test_correction_appends_new_event_and_keeps_original():
    original = event_ledger.append(
        practice_id="wzdm-01", patient_id="p-101", event_type="visit.v1",
        source_type="pms", source_id="src-3", payload={"note": "wrong"},
    )
    correction = event_ledger.correct(
        original.event_id, payload={"note": "right"}, reason="source correction",
        actor_user_id="actor-2",
    )
    assert correction.correction_of == original.event_id
    assert original.superseded_by == correction.event_id
    assert original.payload["note"] == "wrong"
    assert event_ledger.get(original.event_id).payload["note"] == "wrong"
    assert event_ledger.verify() is True


def test_reconstruction_trace():
    original = event_ledger.append(
        practice_id="wzdm-01", patient_id="p-102", event_type="report.v1",
        source_type="family", source_id="src-4", payload={"text": "a"},
    )
    correction = event_ledger.correct(
        original.event_id, payload={"text": "b"}, reason="typo", actor_user_id="actor-3"
    )
    trace = event_ledger.reconstruct(correction.event_id)
    assert trace["original_event_id"] == original.event_id
    assert trace["corrections"] == [correction.event_id]
    assert len(trace["events"]) == 2
    assert trace["verified"] is True


def test_idempotency_replay_and_key_reuse():
    key = "idem-test-1"
    request = {"patient_id": "p-103", "event_type": "visit.v1"}
    first, replayed = event_ledger.execute_idempotent("append", key, request, lambda: {"event_id": "e1"})
    assert replayed is False
    second, replayed = event_ledger.execute_idempotent("append", key, request, lambda: {"event_id": "e2"})
    assert replayed is True
    assert second == first
    with pytest.raises(AuthzError) as exc:
        event_ledger.execute_idempotent(
            "append", key, {"patient_id": "p-999"}, lambda: {"event_id": "e3"}
        )
    assert exc.value.code == "IDEMPOTENCY_KEY_REUSE"


def test_outbox_pending_then_dispatch():
    event_ledger.append(
        practice_id="wzdm-01", patient_id="p-104", event_type="visit.v1",
        source_type="pms", source_id="src-5", payload={},
    )
    assert len(event_ledger.pending_outbox()) >= 1
    count = event_ledger.dispatch_outbox()
    assert count >= 1
    assert len(event_ledger.pending_outbox()) == 0


def test_api_append_requires_idempotency_key_and_role():
    s = _session("orthodontist")
    body = {
        "patient_id": "p-200", "event_type": "visit.v1",
        "source_type": "pms", "source_id": "api-1", "payload": {"x": 1},
    }
    missing = client.post("/v1/events", json=body, headers=_headers(s))
    assert missing.status_code == 400

    ok = client.post(
        "/v1/events", json=body,
        headers={**_headers(s), "Idempotency-Key": "api-idem-1"},
    )
    assert ok.status_code == 200
    assert ok.json()["replayed"] is False

    replay = client.post(
        "/v1/events", json=body,
        headers={**_headers(s), "Idempotency-Key": "api-idem-1"},
    )
    assert replay.json()["replayed"] is True

    guardian = _session("guardian")
    denied = client.post(
        "/v1/events", json=body,
        headers={**_headers(guardian), "Idempotency-Key": "api-idem-2"},
    )
    assert denied.status_code == 403


def test_api_correction_requires_step_up():
    from datetime import datetime, timedelta, timezone

    s = _session("orthodontist")
    s.assurance = "medium"
    s.last_auth_at = datetime.now(timezone.utc) - timedelta(hours=1)
    event = event_ledger.append(
        practice_id="wzdm-01", patient_id="p-201", event_type="visit.v1",
        source_type="pms", source_id="api-2", payload={},
    )
    no_step = client.post(
        f"/v1/events/{event.event_id}/corrections",
        json={"payload": {"fixed": True}, "reason": "fix"},
        headers=_headers(s),
    )
    assert no_step.status_code == 401

    session_store.step_up(s.session_id)
    stepped = client.post(
        f"/v1/events/{event.event_id}/corrections",
        json={"payload": {"fixed": True}, "reason": "fix"},
        headers=_headers(s),
    )
    assert stepped.status_code == 200


def test_api_verify_requires_manager():
    manager = _session("practice_manager")
    assert client.get("/v1/events/ledger/verify", headers=_headers(manager)).status_code == 200
    assistant = _session("clinical_assistant")
    assert client.get("/v1/events/ledger/verify", headers=_headers(assistant)).status_code == 403
