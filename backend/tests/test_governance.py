"""Governed rule/content lifecycle tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.governance_service import GovernanceError, governance_service
from app.services.session_service import session_store

client = TestClient(app)


def _session(role, user):
    return session_store.create(
        user_id=user, assurance="high", auth_methods=["oidc", "mfa"],
        practice_id="wzdm-01", membership_id=f"m-{user}", roles=[role],
    )


def _headers(s):
    return {"Authorization": f"Bearer {s.session_id}"}


def _rule(name="Debond loop"):
    return {"name": name, "when": "debond", "operators": ["clock", "deadline"]}


def test_forbidden_operators_rejected():
    author = _session("practice_manager", "gov-author")
    with pytest.raises(GovernanceError) as exc:
        governance_service.create_version("rule", "wzdm-01", {"name": "x", "when": "y", "operators": ["ai"]}, author)
    assert exc.value.code == "FORBIDDEN_OPERATOR"


def test_lifecycle_draft_submit_approve_activate():
    author = _session("practice_manager", "gov-author2")
    approver = _session("orthodontist", "gov-approver")
    version = governance_service.create_version("rule", "wzdm-01", _rule(), author)
    assert version.state == "DRAFT"
    governance_service.submit(version.version_id, author)
    assert version.state == "SUBMITTED"
    approved = governance_service.approve(version.version_id, approver)
    assert approved.state == "APPROVED"
    assert approved.approver_user_id == approver.user_id
    active = governance_service.activate(version.version_id, author, "2026-11-27T00:00:00Z")
    assert active.state == "ACTIVE"
    assert active.effective_from == "2026-11-27T00:00:00Z"


def test_author_cannot_approve():
    author = _session("practice_manager", "gov-author3")
    version = governance_service.create_version("rule", "wzdm-01", _rule(), author)
    governance_service.submit(version.version_id, author)
    with pytest.raises(GovernanceError) as exc:
        governance_service.approve(version.version_id, author)
    assert exc.value.code == "AUTHOR_CANNOT_APPROVE"


def test_editing_body_invalidates_approval():
    author = _session("practice_manager", "gov-author4")
    approver = _session("orthodontist", "gov-approver4")
    version = governance_service.create_version("rule", "wzdm-01", _rule(), author)
    governance_service.submit(version.version_id, author)
    governance_service.approve(version.version_id, approver)
    version.body["when"] = "changed after approval"
    with pytest.raises(GovernanceError) as exc:
        governance_service.activate(version.version_id, author)
    assert exc.value.code == "APPROVAL_INVALIDATED"
    assert version.state == "DRAFT"


def test_activation_supersedes_previous_active():
    author = _session("practice_manager", "gov-author5")
    approver = _session("orthodontist", "gov-approver5")
    first = governance_service.create_version("rule", "wzdm-01", _rule("Loop A"), author)
    governance_service.submit(first.version_id, author)
    governance_service.approve(first.version_id, approver)
    governance_service.activate(first.version_id, author)

    second = governance_service.create_version("rule", "wzdm-01", _rule("Loop B"), author, replaces=first.version_id)
    governance_service.submit(second.version_id, author)
    governance_service.approve(second.version_id, approver)
    governance_service.activate(second.version_id, author)
    assert first.state == "WITHDRAWN"
    assert second.state == "ACTIVE"


def test_safety_withdrawal_keeps_bytes():
    author = _session("practice_manager", "gov-author6")
    approver = _session("orthodontist", "gov-approver6")
    version = governance_service.create_version("content", "wzdm-01", {"title": "Guide", "text": "Approved text"}, author)
    governance_service.submit(version.version_id, author)
    governance_service.approve(version.version_id, approver)
    governance_service.activate(version.version_id, author)
    checksum = version.checksum
    withdrawn = governance_service.withdraw(version.version_id, "unsafe instruction", author)
    assert withdrawn.state == "WITHDRAWN"
    assert withdrawn.checksum == checksum


def test_api_role_enforcement():
    manager = _session("practice_manager", "gov-mgr-api")
    assistant = _session("clinical_assistant", "gov-asst-api")
    dentist = _session("orthodontist", "gov-dent-api")

    created = client.post(
        "/v1/governance/content/versions",
        json={"body": {"title": "Care", "text": "Approved wording"}},
        headers=_headers(manager),
    )
    assert created.status_code == 200
    version_id = created.json()["version_id"]

    denied = client.post(
        f"/v1/governance/versions/{version_id}/submit", json={}, headers=_headers(assistant)
    )
    assert denied.status_code == 403

    client.post(f"/v1/governance/versions/{version_id}/submit", json={}, headers=_headers(manager))
    approved = client.post(
        f"/v1/governance/versions/{version_id}/approve", json={}, headers=_headers(dentist)
    )
    assert approved.status_code == 200
    assert approved.json()["state"] == "APPROVED"
