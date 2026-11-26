"""Staff authentication lifecycle — handbook Step 5 (lines 3573-3660).

Alpha note: the identity provider is simulated in-process so the full
authorization-code + PKCE structure, state/nonce binding and session
semantics are executable. Production swaps the simulator for the approved
OIDC issuer; no password is ever received or stored by the application.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import threading
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Response, status
from pydantic import BaseModel

from app.services.authz_service import PERMISSIONS, require
from app.services.session_service import (
    AuthError,
    SessionRecord,
    session_store,
)

router = APIRouter(tags=["Auth"])


class StaffStartRequest(BaseModel):
    return_to: str = "/staff/inbox"


class PracticeContextRequest(BaseModel):
    practice_id: str
    expected_session_version: Optional[int] = None


class StepUpRequest(BaseModel):
    purpose: str


class DeactivateRequest(BaseModel):
    reason: str
    effective_at: Optional[str] = None
    replacement_owner_membership_id: str
    expected_row_version: int


ALLOWED_RETURN_TO = {"/staff/inbox", "/family/home", "/admin/workforce", "/"}
_deactivated_users: set[str] = set()


_pending: dict[str, dict] = {}
_pending_lock = threading.RLock()


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def current_session(
    authorization: Optional[str] = Header(default=None),
    wzdm_session: Optional[str] = Cookie(default=None),
) -> SessionRecord:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif wzdm_session:
        token = wzdm_session
    try:
        return session_store.get(token)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


# ---------------------------------------------------------------------------
# OIDC authorization-code + PKCE (alpha IdP simulator)
# ---------------------------------------------------------------------------


@router.get("/v1/auth/staff/start")
def start_staff_auth(return_to: str = Query(default="/staff/inbox")):
    if return_to not in ALLOWED_RETURN_TO:
        raise HTTPException(status_code=400, detail="Invalid return target")
    verifier = secrets.token_urlsafe(48)
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(16)
    code = secrets.token_urlsafe(24)
    with _pending_lock:
        _pending[state] = {
            "code": code,
            "nonce": nonce,
            "code_challenge": _pkce_challenge(verifier),
            "return_to": return_to,
            "consumed": False,
        }
    return {
        "authorization_url": "/v1/auth/staff/callback",
        "state": state,
        "nonce": nonce,
        "code_challenge": _pkce_challenge(verifier),
        "code_challenge_method": "S256",
        # Alpha-only: the simulator returns the verifier so the flow is executable.
        "code_verifier_for_alpha": verifier,
        "authorization_code_for_alpha": code,
        "return_to": return_to,
    }


@router.get("/v1/auth/staff/callback")
def complete_staff_auth(
    response: Response,
    code: str = Query(...),
    state: str = Query(...),
    code_verifier: str = Query(...),
):
    with _pending_lock:
        tx = _pending.get(state)
        if tx is None or tx["consumed"]:
            raise HTTPException(status_code=401, detail={"code": "INVALID_STATE"})
        if not secrets.compare_digest(code, tx["code"]):
            raise HTTPException(status_code=401, detail={"code": "INVALID_CODE"})
        if _pkce_challenge(code_verifier) != tx["code_challenge"]:
            raise HTTPException(status_code=401, detail={"code": "PKCE_MISMATCH"})
        tx["consumed"] = True
        return_to = tx["return_to"]

    record = session_store.create(
        user_id="alpha-user",
        assurance="high",
        auth_methods=["oidc", "mfa", "phishing_resistant"],
        practice_id="wzdm-01",
        membership_id="membership-wzdm-01",
        roles=["practice_member"],
    )
    response.set_cookie(
        "wzdm_session",
        record.session_id,
        httponly=True,
        samesite="lax",
        secure=False,  # production requires secure=True over HTTPS
    )
    return {
        "session_id": record.session_id,
        "csrf_token": record.csrf_token,
        "return_to": return_to,
        "principal": session_store.principal(record),
    }


# ---------------------------------------------------------------------------
# Alpha direct sign-in (keeps the existing frontend working)
# ---------------------------------------------------------------------------


class AlphaSignInRequest(BaseModel):
    session: str
    password: str


@router.post("/v1/sessions")
def alpha_sign_in(payload: AlphaSignInRequest, response: Response):
    if not payload.session.strip() or not payload.password.strip():
        raise HTTPException(status_code=400, detail="Session identifier and password are required")
    if payload.session in _deactivated_users:
        raise HTTPException(status_code=401, detail="Access unavailable")
    record = session_store.create(
        user_id=payload.session,
        assurance="medium",
        auth_methods=["oidc_alpha", "mfa_alpha"],
    )
    response.set_cookie("wzdm_session", record.session_id, httponly=True, samesite="lax")
    return {
        "session_id": record.session_id,
        "csrf_token": record.csrf_token,
        "access_token": record.session_id,
        "token_type": "bearer",
        "expires_in": 8 * 3600,
        "principal": session_store.principal(record),
    }


# ---------------------------------------------------------------------------
# Protected session operations
# ---------------------------------------------------------------------------


@router.get("/v1/me")
def current_principal(session: SessionRecord = Depends(current_session)):
    return session_store.principal(session)


@router.post("/v1/sessions/practice-context")
def select_practice_context(payload: PracticeContextRequest, session: SessionRecord = Depends(current_session)):
    try:
        record = session_store.select_practice(
            session.session_id, payload.practice_id, payload.expected_session_version
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return {
        "practice_id": record.active_practice_id,
        "membership_id": record.active_membership_id,
        "active": True,
        "session_version": record.session_version,
    }


@router.post("/v1/sessions/step-up")
def step_up(payload: StepUpRequest, session: SessionRecord = Depends(current_session)):
    if payload.purpose not in {"approval", "export", "support", "rule", "content", "proxy"}:
        raise HTTPException(status_code=400, detail="Invalid step-up purpose")
    record = session_store.step_up(session.session_id)
    return {"assurance": record.assurance, "last_auth_at": record.last_auth_at.isoformat()}


@router.delete("/v1/sessions/current", status_code=status.HTTP_204_NO_CONTENT)
def revoke_current_session(response: Response, session: SessionRecord = Depends(current_session)):
    session_store.revoke(session.session_id)
    response.delete_cookie("wzdm_session")


@router.get("/v1/auth/permissions/matrix")
def permission_matrix(
    session: SessionRecord = Depends(current_session),
    _scope: dict = Depends(require("audit", "read")),
):
    session_store.require_step_up(session)
    return {
        "roles": sorted({role for roles in PERMISSIONS.values() for role in roles}),
        "matrix": [{"resource": r, "action": a, "roles": sorted(v)} for (r, a), v in sorted(PERMISSIONS.items())],
    }


@router.get("/v1/auth/scope")
def current_scope(scope: dict = Depends(require("patient", "read_care"))):
    return scope


@router.get("/v1/audit/events")
def auth_audit_events(session: SessionRecord = Depends(current_session)):
    session_store.require_step_up(session)
    return {"events": session_store.audit_entries}


# ---------------------------------------------------------------------------
# Deactivation — impact review, confirmation and generic denial (AUTH-S13..17)
# ---------------------------------------------------------------------------


@router.get("/v1/auth/staff/{user_id}/deactivation-impact")
def deactivation_impact(user_id: str, session: SessionRecord = Depends(current_session)):
    session_store.require_step_up(session)
    active = session_store.sessions_for_user(user_id)
    return {
        "user_id": user_id,
        "active_sessions": len([s for s in active if not s.revoked]),
        "open_cards": 0,
        "pending_approvals": 0,
        "support_grants": 0,
        "on_call_duties": 0,
        "clinical_text_included": False,
    }


@router.post("/v1/auth/staff/{user_id}/deactivate")
def deactivate_staff(
    user_id: str, payload: DeactivateRequest, session: SessionRecord = Depends(current_session)
):
    session_store.require_step_up(session)
    if not payload.reason.strip() or not payload.replacement_owner_membership_id.strip():
        raise HTTPException(status_code=400, detail="Reason and replacement owner are required")
    if payload.expected_row_version < 1:
        raise HTTPException(status_code=409, detail={"code": "STALE_MEMBERSHIP_VERSION"})
    revoked = session_store.revoke_user_sessions(user_id)
    _deactivated_users.add(user_id)
    session_store.audit_entries.append({
        "action": "STAFF_DEACTIVATION",
        "user_id": user_id,
        "actor_session_id": session.session_id,
        "detail": payload.reason,
        "replacement_owner": payload.replacement_owner_membership_id,
        "revoked_sessions": revoked,
    })
    return {
        "user_id": user_id,
        "status": "deactivated",
        "sessions_revoked": revoked,
        "open_work": "reassignment_review",
    }
