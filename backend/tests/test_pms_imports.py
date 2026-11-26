"""PMS import tests — quarantine, dry run, atomic commit and correction."""

import base64
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.services.event_ledger import event_ledger
from app.services.pms_service import ImportError, pms_service
from app.services.session_service import session_store

client = TestClient(app)

def VALID_CSV(tag="a"):
    return f"patient_ref,event_date,event_type\np-9{tag}0,2026-11-20,visit\np-9{tag}1,2026-11-21,adjustment\n".encode()


def INVALID_CSV(tag="b"):
    return f"patient_ref,event_date,event_type\np-9{tag}2,2026-11-20,unknown_type\n,2026-11-21,visit\n".encode()


def _manager(stale=False):
    s = session_store.create(
        user_id="import-manager", assurance="high", auth_methods=["oidc", "mfa"],
        practice_id="wzdm-01", membership_id="m-manager", roles=["practice_manager"],
    )
    if stale:
        s.assurance = "medium"
        s.last_auth_at = datetime.now(timezone.utc) - timedelta(hours=1)
    return s


def _headers(s):
    return {"Authorization": f"Bearer {s.session_id}"}


def test_quarantine_and_hash():
    batch = pms_service.quarantine("wzdm-01", "export.csv", VALID_CSV("1"))
    assert batch.state == "QUARANTINED"
    assert len(batch.rows) == 2
    assert len(batch.sha256) == 64


def test_dry_run_validates_without_writing_care_events():
    batch = pms_service.quarantine("wzdm-01", "export.csv", VALID_CSV("2"))
    before = len(event_ledger._order)
    result = pms_service.dry_run(batch.import_id)
    assert result["valid"] == 2
    assert result["invalid"] == 0
    assert result["isolated"] is True
    assert len(event_ledger._order) == before


def test_dry_run_reports_invalid_rows():
    batch = pms_service.quarantine("wzdm-01", "bad.csv", INVALID_CSV("3"))
    result = pms_service.dry_run(batch.import_id)
    assert result["invalid"] == 2
    assert any("unsupported_event_type" in v for v in result["issues"].values())
    assert any("missing:patient_ref" in v for v in result["issues"].values())


def test_commit_requires_dry_run_and_writes_events():
    batch = pms_service.quarantine("wzdm-01", "export.csv", VALID_CSV("4"))
    try:
        pms_service.commit(batch.import_id)
    except ImportError as exc:
        assert exc.code == "DRY_RUN_REQUIRED"
    else:
        raise AssertionError("expected dry run requirement")

    pms_service.dry_run(batch.import_id)
    before = len(event_ledger._order)
    result = pms_service.commit(batch.import_id, "import-manager")
    assert result["state"] == "COMMITTED"
    assert result["rows_written"] == 2
    assert len(event_ledger._order) == before + 2


def test_duplicate_package_cannot_commit_twice():
    first = pms_service.quarantine("wzdm-01", "export.csv", VALID_CSV("5"))
    pms_service.dry_run(first.import_id)
    pms_service.commit(first.import_id)
    try:
        pms_service.quarantine("wzdm-01", "export.csv", VALID_CSV("5"))
    except ImportError as exc:
        assert exc.code == "DUPLICATE_COMMITTED_PACKAGE"
    else:
        raise AssertionError("expected duplicate rejection")


def test_compensating_correction_appends_events():
    batch = pms_service.quarantine("wzdm-01", "export.csv", VALID_CSV("6"))
    pms_service.dry_run(batch.import_id)
    pms_service.commit(batch.import_id)
    before = len(event_ledger._order)
    result = pms_service.compensating_correction(batch.import_id, "source mapping was wrong", "manager")
    assert result["corrected_rows"] == 2
    assert len(event_ledger._order) == before + 2


def test_api_requires_manager_and_step_up():
    manager = _manager(stale=True)
    encoded = base64.b64encode(VALID_CSV("7")).decode()
    denied = client.post(
        "/v1/pms-imports/packages",
        json={"filename": "e.csv", "content_base64": encoded},
        headers=_headers(manager),
    )
    assert denied.status_code == 401

    manager = _manager()
    ok = client.post(
        "/v1/pms-imports/packages",
        json={"filename": "e.csv", "content_base64": encoded},
        headers=_headers(manager),
    )
    assert ok.status_code == 200
    import_id = ok.json()["import_id"]

    dry = client.post(
        f"/v1/pms-imports/{import_id}/dry-run", json={}, headers=_headers(manager)
    )
    assert dry.status_code == 200

    assistant = session_store.create(
        user_id="import-assistant", assurance="high", auth_methods=["oidc"],
        practice_id="wzdm-01", membership_id="m-a", roles=["clinical_assistant"],
    )
    forbidden = client.get(
        f"/v1/pms-imports/{import_id}", headers=_headers(assistant)
    )
    assert forbidden.status_code == 403
