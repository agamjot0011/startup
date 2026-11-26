"""Step 6 authorization matrix — six roles, two tenants, privacy and grants."""

from datetime import datetime, timedelta, timezone

from app.services.authz_service import (
    AuthzError,
    SupportGrant,
    authorize,
    register_support_grant,
)
from app.services.session_service import session_store


def _session(role, practice="wzdm-01", assurance="high"):
    record = session_store.create(
        user_id=f"user-{role}-{practice}",
        assurance=assurance,
        auth_methods=["oidc", "mfa"],
        practice_id=practice,
        membership_id=f"membership-{practice}",
        roles=[role],
    )
    return record


def _allow(session, resource, action, **kwargs):
    assert authorize(session, resource, action, **kwargs)["allowed"] is True


def _deny(session, resource, action, code, **kwargs):
    try:
        authorize(session, resource, action, **kwargs)
    except AuthzError as exc:
        assert exc.code == code
    else:
        raise AssertionError(f"expected denial {code} for {resource}:{action}")


def test_orthodontist_allowed_actions():
    s = _session("orthodontist")
    _allow(s, "patient", "read_care")
    _allow(s, "card", "acknowledge")
    _allow(s, "report", "triage")
    _allow(s, "brief", "sign")
    _allow(s, "rule", "approve")


def test_clinical_assistant_allowed_and_denied():
    s = _session("clinical_assistant")
    _allow(s, "card", "result")
    _deny(s, "report", "triage", "NO_PERMITTED_ROLE")
    _deny(s, "brief", "sign", "NO_PERMITTED_ROLE")


def test_front_desk_scope():
    s = _session("front_desk")
    _allow(s, "booking", "manage")
    _allow(s, "promise", "manage")
    _deny(s, "card", "result", "NO_PERMITTED_ROLE")


def test_practice_manager_scope():
    s = _session("practice_manager")
    _allow(s, "operations", "read")
    _allow(s, "audit", "read")
    _allow(s, "export", "create")
    _deny(s, "report", "triage", "NO_PERMITTED_ROLE")


def test_patient_scope_is_own_patient_only():
    s = _session("patient")
    _allow(s, "patient", "read_own", patient_id="p-1", subject_patient_id="p-1")
    _deny(s, "patient", "read_own", "PATIENT_SCOPE_DENIED", patient_id="p-2", subject_patient_id="p-1")


def test_guardian_requires_verified_relationship_and_consent():
    s = _session("guardian")
    _deny(s, "patient", "read_linked", "RELATIONSHIP_OR_CONSENT_REQUIRED",
          patient_id="p-1", subject_patient_id="p-1", relationship_verified=True, consent_active=False)
    _allow(s, "patient", "read_linked", patient_id="p-1", subject_patient_id="p-1",
           relationship_verified=True, consent_active=True)


def test_cross_tenant_denial():
    s = _session("orthodontist", practice="wzdm-01")
    _deny(s, "patient", "read_care", "TENANT_MISMATCH", practice_id="wzdm-02")


def test_no_practice_context_denied():
    s = session_store.create(user_id="no-context", roles=["orthodontist"], practice_id=None)
    _deny(s, "patient", "read_care", "NO_PRACTICE_CONTEXT")


def test_unknown_permission_denied():
    s = _session("orthodontist")
    _deny(s, "nonsense", "fly", "UNKNOWN_PERMISSION")


def test_support_grant_requires_ticket_scope_and_fresh_auth():
    s = _session("orthodontist")
    now = datetime.now(timezone.utc)
    register_support_grant(SupportGrant(
        practice_id="wzdm-01",
        scope="audit:read",
        ticket_reference="SUP-900",
        approved_by="manager-1",
        effective_from=now - timedelta(minutes=1),
        effective_to=now + timedelta(hours=1),
    ))
    # Orthodontist has no audit permission, so the grant path is used.
    result = authorize(s, "audit", "read", support_ticket="SUP-900")
    assert result["via_support_grant"] is True

    expired = _session("orthodontist")
    register_support_grant(SupportGrant(
        practice_id="wzdm-01",
        scope="audit:read",
        ticket_reference="SUP-901",
        approved_by="manager-1",
        effective_from=now - timedelta(hours=2),
        effective_to=now - timedelta(hours=1),
    ))
    _deny(expired, "audit", "read", "SUPPORT_GRANT_INVALID", support_ticket="SUP-901")


def test_permission_matrix_endpoint_denies_non_manager():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    manager = _session("practice_manager")
    session_store.step_up(manager.session_id)
    headers = {"Authorization": f"Bearer {manager.session_id}"}
    r = client.get("/v1/auth/permissions/matrix", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["matrix"]) >= 10

    assistant = _session("clinical_assistant")
    session_store.step_up(assistant.session_id)
    denied = client.get(
        "/v1/auth/permissions/matrix",
        headers={"Authorization": f"Bearer {assistant.session_id}"},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "NO_PERMITTED_ROLE"


def test_scope_endpoint_enforces_role():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    dentist = _session("orthodontist")
    r = client.get(
        "/v1/auth/scope", headers={"Authorization": f"Bearer {dentist.session_id}"}
    )
    assert r.status_code == 200
    assert r.json()["allowed"] is True

    guardian = _session("guardian")
    denied = client.get(
        "/v1/auth/scope", headers={"Authorization": f"Bearer {guardian.session_id}"}
    )
    assert denied.status_code == 403
