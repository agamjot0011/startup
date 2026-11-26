"""Server-side authorization — handbook Step 6 / overview steps 6 and 10.

Implements least-privilege role permissions, tenant isolation, patient/guardian
privacy scopes, verified relationship and consent requirements, and expiring
ticketed support grants. No route may rely on client-supplied role claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException

from app.services.session_service import AuthError, SessionRecord, session_store

ROLES = {
    "patient",
    "guardian",
    "clinical_assistant",
    "orthodontist",
    "front_desk",
    "practice_manager",
}

STAFF_ROLES = {"clinical_assistant", "orthodontist", "front_desk", "practice_manager"}
FAMILY_ROLES = {"patient", "guardian"}

# (resource, action) -> permitted roles
PERMISSIONS: dict[tuple[str, str], set[str]] = {
    ("patient", "read_own"): {"patient"},
    ("patient", "read_linked"): {"guardian"},
    ("patient", "read_care"): STAFF_ROLES,
    ("card", "read"): STAFF_ROLES,
    ("card", "acknowledge"): {"clinical_assistant", "orthodontist", "front_desk"},
    ("card", "result"): {"clinical_assistant", "orthodontist"},
    ("report", "create"): {"patient", "guardian"},
    ("report", "triage"): {"orthodontist"},
    ("brief", "sign"): {"orthodontist"},
    ("booking", "manage"): {"front_desk"},
    ("promise", "manage"): {"front_desk"},
    ("operations", "read"): {"practice_manager"},
    ("audit", "read"): {"practice_manager"},
    ("export", "create"): {"practice_manager"},
    ("rule", "approve"): {"orthodontist", "practice_manager"},
    ("content", "approve"): {"orthodontist", "practice_manager"},
    ("support_grant", "approve"): {"practice_manager"},
}


class AuthzError(Exception):
    def __init__(self, code: str, status: int = 403, message: str = "") -> None:
        self.code = code
        self.status = status
        self.message = message or code
        super().__init__(self.message)


@dataclass
class SupportGrant:
    practice_id: str
    scope: str
    ticket_reference: str
    approved_by: str
    effective_from: datetime
    effective_to: datetime
    revoked: bool = False

    def active(self, now: datetime) -> bool:
        return (
            not self.revoked
            and self.effective_from <= now <= self.effective_to
        )


_grants: list[SupportGrant] = []


def register_support_grant(grant: SupportGrant) -> None:
    _grants.append(grant)


def authorize(
    session: SessionRecord,
    resource: str,
    action: str,
    *,
    practice_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    subject_patient_id: Optional[str] = None,
    relationship_verified: bool = False,
    consent_active: bool = False,
    support_ticket: Optional[str] = None,
    require_fresh_auth: bool = False,
) -> dict:
    """Authorize an action and return the effective scope descriptor.

    Raises AuthzError on any denial. Nothing here trusts a client role claim:
    roles come from the server-side session record only.
    """
    if session.revoked:
        raise AuthzError("SESSION_REVOKED", 401)
    if not session.active_practice_id:
        raise AuthzError("NO_PRACTICE_CONTEXT", 403)

    roles = set(session.roles) & ROLES
    if not roles:
        raise AuthzError("NO_PERMITTED_ROLE", 403)

    granted = PERMISSIONS.get((resource, action))
    if granted is None:
        raise AuthzError("UNKNOWN_PERMISSION", 403)

    effective_roles = roles & granted
    grant = None
    if not effective_roles and support_ticket:
        now = datetime.now(timezone.utc)
        for candidate in _grants:
            if (
                candidate.ticket_reference == support_ticket
                and candidate.practice_id == session.active_practice_id
                and candidate.scope == f"{resource}:{action}"
                and candidate.active(now)
            ):
                grant = candidate
                break
        if grant is None:
            raise AuthzError("SUPPORT_GRANT_INVALID", 403)
        session_store.require_step_up(session)

    if not effective_roles and grant is None:
        raise AuthzError("NO_PERMITTED_ROLE", 403)

    # Tenant isolation — staff and support access is bound to the active practice.
    if practice_id is not None and practice_id != session.active_practice_id:
        raise AuthzError("TENANT_MISMATCH", 403)

    # Family privacy scopes.
    if "patient" in effective_roles or "guardian" in effective_roles:
        if patient_id is None or subject_patient_id is None or patient_id != subject_patient_id:
            raise AuthzError("PATIENT_SCOPE_DENIED", 403)
    if "guardian" in effective_roles and action == "read_linked":
        if not relationship_verified or not consent_active:
            raise AuthzError("RELATIONSHIP_OR_CONSENT_REQUIRED", 403)

    if require_fresh_auth:
        session_store.require_step_up(session)

    session_store.audit_entries.append({
        "action": "AUTHZ_DECISION",
        "user_id": session.user_id,
        "session_id": session.session_id,
        "practice_id": session.active_practice_id,
        "detail": f"{resource}:{action}",
        "result": "allow",
        "roles": sorted(effective_roles) if effective_roles else ["support_grant"],
    })

    return {
        "allowed": True,
        "roles": sorted(effective_roles) if effective_roles else ["support_grant"],
        "practice_id": session.active_practice_id,
        "patient_id": patient_id,
        "via_support_grant": grant is not None,
    }


def require(resource: str, action: str, **kwargs):
    """FastAPI dependency factory for a permission check."""

    def dependency(session: SessionRecord = Depends(_session_dependency)):
        try:
            return authorize(session, resource, action, **kwargs)
        except AuthzError as exc:
            raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})

    return dependency


def _session_dependency(
    authorization: Optional[str] = Header(default=None),
    wzdm_session: Optional[str] = Cookie(default=None),
):
    from app.api.routes.auth import current_session

    return current_session(authorization=authorization, wzdm_session=wzdm_session)
