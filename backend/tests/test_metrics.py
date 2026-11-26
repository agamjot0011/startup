"""Metric fact tests — contracts, provenance and independent recomputation."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.event_ledger import event_ledger
from app.services.metrics_service import METRIC_DEFINITIONS, metrics_service
from app.services.session_service import session_store

client = TestClient(app)


def _manager():
    return session_store.create(
        user_id="metrics-manager", assurance="high", auth_methods=["oidc", "mfa"],
        practice_id="wzdm-01", membership_id="m-manager", roles=["practice_manager"],
    )


def _assistant():
    return session_store.create(
        user_id="metrics-assistant", assurance="high", auth_methods=["oidc"],
        practice_id="wzdm-01", membership_id="m-a", roles=["clinical_assistant"],
    )


def _headers(s):
    return {"Authorization": f"Bearer {s.session_id}"}


def test_recompute_produces_all_ten_contracts():
    facts = metrics_service.recompute()
    assert {f.metric_id for f in facts} == set(METRIC_DEFINITIONS)
    for fact in facts:
        assert fact.definition_version == "v1"
        assert fact.input_hash
        assert fact.provisional is True


def test_verify_is_reproducible():
    result = metrics_service.verify()
    assert result["reproducible"] is True
    assert result["metrics"] == 10


def test_input_hash_changes_with_new_events():
    before = {f.metric_id: f.input_hash for f in metrics_service.recompute()}
    event_ledger.append(
        practice_id="wzdm-01", patient_id="p-metric", event_type="metric_probe.v1",
        source_type="test", source_id="probe", payload={},
    )
    after = {f.metric_id: f.input_hash for f in metrics_service.recompute()}
    assert before != after


def test_api_manager_only():
    manager = _manager()
    ok = client.get("/v1/metrics", headers=_headers(manager))
    assert ok.status_code == 200
    assert len(ok.json()["facts"]) == 10
    assert ok.json()["provisional_baseline"] is True

    denied = client.get("/v1/metrics", headers=_headers(_assistant()))
    assert denied.status_code == 403

    one = client.get("/v1/metrics/MET-01", headers=_headers(manager))
    assert one.status_code == 200
    assert one.json()["metric_id"] == "MET-01"

    missing = client.get("/v1/metrics/MET-99", headers=_headers(manager))
    assert missing.status_code == 404
