"""Handbook Step 5 — staff authentication lifecycle tests."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.session_service import session_store

client = TestClient(app)


def _authorization(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _complete_oidc() -> dict:
    start = client.get("/v1/auth/staff/start?return_to=/staff/inbox").json()
    callback = client.get(
        "/v1/auth/staff/callback",
        params={
            "code": start["authorization_code_for_alpha"],
            "state": start["state"],
            "code_verifier": start["code_verifier_for_alpha"],
        },
    )
    assert callback.status_code == 200, callback.text
    return callback.json()


def test_oidc_start_binds_state_nonce_and_pkce():
    r = client.get("/v1/auth/staff/start?return_to=/staff/inbox")
    assert r.status_code == 200
    body = r.json()
    assert body["code_challenge_method"] == "S256"
    assert body["state"] and body["nonce"] and body["code_challenge"]


def test_oidc_start_rejects_unlisted_return_target():
    assert client.get("/v1/auth/staff/start?return_to=/evil").status_code == 400


def test_callback_rejects_bad_state_and_bad_pkce():
    start = client.get("/v1/auth/staff/start").json()
    bad_state = client.get(
        "/v1/auth/staff/callback",
        params={
            "code": start["authorization_code_for_alpha"],
            "state": "not-the-state",
            "code_verifier": start["code_verifier_for_alpha"],
        },
    )
    assert bad_state.status_code == 401

    bad_pkce = client.get(
        "/v1/auth/staff/callback",
        params={
            "code": start["authorization_code_for_alpha"],
            "state": start["state"],
            "code_verifier": "wrong-verifier",
        },
    )
    assert bad_pkce.status_code == 401


def test_callback_creates_high_assurance_session():
    body = _complete_oidc()
    assert body["principal"]["assurance"] == "high"
    assert "phishing_resistant" in body["principal"]["auth_methods"]
    assert body["csrf_token"]
    assert body["return_to"] == "/staff/inbox"


def test_me_requires_session_and_returns_principal():
    client.cookies.clear()
    assert client.get("/v1/me").status_code == 401
    body = _complete_oidc()
    r = client.get("/v1/me", headers=_authorization(body["session_id"]))
    assert r.status_code == 200
    assert r.json()["user_id"] == "alpha-user"


def test_practice_context_rejects_stale_version():
    body = _complete_oidc()
    token = body["session_id"]
    first = client.post(
        "/v1/sessions/practice-context",
        json={"practice_id": "wzdm-02", "expected_session_version": body["principal"]["session_version"]},
        headers=_authorization(token),
    )
    assert first.status_code == 200
    assert first.json()["session_version"] == 2

    stale = client.post(
        "/v1/sessions/practice-context",
        json={"practice_id": "wzdm-01", "expected_session_version": 1},
        headers=_authorization(token),
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "STALE_SESSION_VERSION"


def test_step_up_and_audit_require_recent_auth():
    body = _complete_oidc()
    token = body["session_id"]
    assert client.get("/v1/audit/events", headers=_authorization(token)).status_code == 200
    up = client.post(
        "/v1/sessions/step-up", json={"purpose": "approval"}, headers=_authorization(token)
    )
    assert up.status_code == 200
    assert up.json()["assurance"] == "high"
    actions = [e["action"] for e in session_store.audit_entries]
    assert "SESSION_CREATE" in actions
    assert "SESSION_STEP_UP" in actions


def test_step_up_rejects_invalid_purpose():
    body = _complete_oidc()
    r = client.post(
        "/v1/sessions/step-up", json={"purpose": "anything"}, headers=_authorization(body["session_id"])
    )
    assert r.status_code == 400


def test_revocation_ends_session():
    body = _complete_oidc()
    token = body["session_id"]
    r = client.delete("/v1/sessions/current", headers=_authorization(token))
    assert r.status_code == 204
    assert client.get("/v1/me", headers=_authorization(token)).status_code == 401


def test_alpha_sign_in_creates_real_session():
    r = client.post("/v1/sessions", json={"session": "nurse-1", "password": "anything"})
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] != "synthetic"
    assert client.get("/v1/me", headers=_authorization(body["session_id"])).status_code == 200


def test_alpha_sign_in_rejects_empty_credentials():
    assert client.post("/v1/sessions", json={"session": "", "password": "x"}).status_code == 400


def test_deactivation_revokes_sessions_and_blocks_login():
    sign_in = client.post(
        "/v1/sessions", json={"session": "departing-user", "password": "x"}
    ).json()
    actor = _complete_oidc()
    headers = _authorization(actor["session_id"])

    impact = client.get(
        "/v1/auth/staff/departing-user/deactivation-impact", headers=headers
    )
    assert impact.status_code == 200
    assert impact.json()["clinical_text_included"] is False

    result = client.post(
        "/v1/auth/staff/departing-user/deactivate",
        json={
            "reason": "role ended",
            "replacement_owner_membership_id": "membership-wzdm-02",
            "expected_row_version": 1,
        },
        headers=headers,
    )
    assert result.status_code == 200
    assert result.json()["status"] == "deactivated"
    assert client.get("/v1/me", headers=_authorization(sign_in["session_id"])).status_code == 401
    denied = client.post(
        "/v1/sessions", json={"session": "departing-user", "password": "x"}
    )
    assert denied.status_code == 401
    assert "tenant" not in denied.text.lower()
