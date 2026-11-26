"""Visit brief sign-off tests — immutable signature and supersession."""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.services.brief_service import BriefError, brief_service
from app.services.session_service import session_store

client = TestClient(app)

EVENTS = [{"event_id": "e1", "type": "visit", "summary": "Adjustment"}]


def _dentist(stale=False):
    s = session_store.create(
        user_id="signing-dentist", assurance="high", auth_methods=["oidc", "mfa"],
        practice_id="wzdm-01", membership_id="membership-orthodontist", roles=["orthodontist"],
    )
    if stale:
        s.assurance = "medium"
        s.last_auth_at = datetime.now(timezone.utc) - timedelta(hours=1)
    return s


def _generate(events=EVENTS):
    return brief_service.generate(
        appointment_id="apt-1", practice_id="wzdm-01", patient_id="p-500", events=events
    )


def test_generated_conclusions_rejected():
    with pytest.raises(BriefError) as exc:
        _generate([{"event_id": "x", "generated_conclusion": "normal"}])
    assert exc.value.code == "GENERATED_CONCLUSION_PROHIBITED"


def test_snapshot_hash_is_deterministic():
    a = _generate()
    b = _generate()
    assert a.snapshot_hash == b.snapshot_hash
    assert a.source_watermark == b.source_watermark
    assert a.public()["signed"] is False


def test_signature_requires_fresh_auth_and_attestation():
    brief = _generate()
    stale = _dentist(stale=True)
    with pytest.raises(BriefError) as exc:
        brief_service.sign(brief.brief_id, actor=stale, attestation="reviewed", expected_row_version=1)
    assert exc.value.code == "REAUTH_REQUIRED"

    dentist = _dentist()
    with pytest.raises(BriefError) as exc:
        brief_service.sign(brief.brief_id, actor=dentist, attestation="", expected_row_version=1)
    assert exc.value.code == "ATTESTATION_REQUIRED"

    signature = brief_service.sign(
        brief.brief_id, actor=dentist, attestation="Reviewed source set", expected_row_version=1
    )
    assert signature.snapshot_hash == brief.snapshot_hash
    assert signature.assurance == "high"
    assert brief_service.get(brief.brief_id).public()["signed"] is True
    with pytest.raises(BriefError) as exc:
        brief_service.sign(brief.brief_id, actor=dentist, attestation="again", expected_row_version=1)
    assert exc.value.code == "ALREADY_SIGNED"


def test_stale_version_rejected():
    brief = _generate()
    dentist = _dentist()
    with pytest.raises(BriefError) as exc:
        brief_service.sign(brief.brief_id, actor=dentist, attestation="x", expected_row_version=99)
    assert exc.value.code == "STALE_BRIEF_VERSION"


def test_supersession_creates_new_version_without_editing_signed_artifact():
    brief = _generate()
    dentist = _dentist()
    signature = brief_service.sign(
        brief.brief_id, actor=dentist, attestation="signed", expected_row_version=1
    )
    replacement = brief_service.supersede(
        brief.brief_id, reason="late source", events=[{"event_id": "e2", "type": "photo"}], actor=dentist
    )
    assert replacement.row_version == 2
    assert brief.superseded_by == replacement.brief_id
    assert brief.signatures[0].signature_id == signature.signature_id
    assert brief.snapshot_hash != replacement.snapshot_hash


def test_api_sign_requires_orthodontist():
    brief = _generate()
    dentist = _dentist()
    headers = {"Authorization": f"Bearer {dentist.session_id}"}
    ok = client.post(
        f"/v1/visit-briefs/{brief.brief_id}/signatures",
        json={"attestation": "Reviewed", "expected_row_version": 1},
        headers=headers,
    )
    assert ok.status_code == 200

    assistant = session_store.create(
        user_id="assistant-1", assurance="high", auth_methods=["oidc"],
        practice_id="wzdm-01", membership_id="m2", roles=["clinical_assistant"],
    )
    denied = client.post(
        f"/v1/visit-briefs/{brief.brief_id}/signatures",
        json={"attestation": "Reviewed", "expected_row_version": 1},
        headers={"Authorization": f"Bearer {assistant.session_id}"},
    )
    assert denied.status_code == 403
