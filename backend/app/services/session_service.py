"""Server-side session lifecycle for the alpha.

Production replaces the in-memory store with a durable, encrypted session
table (see handbook Step 5, lines 3573-3660). The semantics here are real:
opaque identifiers, CSRF tokens, idle and absolute expiry, step-up, explicit
practice context with optimistic versioning, revocation and audit entries.
"""

from __future__ import annotations

import json
import secrets
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services import supabase_store
IDLE_WINDOW = timedelta(minutes=15)
ABSOLUTE_WINDOW = timedelta(hours=8)
STEP_UP_WINDOW = timedelta(minutes=10)


class AuthError(Exception):
    def __init__(self, code: str, status: int = 401, message: str = "") -> None:
        self.code = code
        self.status = status
        self.message = message or code
        super().__init__(self.message)


@dataclass
class SessionRecord:
    session_id: str
    user_id: str
    csrf_token: str
    assurance: str
    auth_methods: list[str]
    active_practice_id: Optional[str] = None
    active_membership_id: Optional[str] = None
    roles: list[str] = field(default_factory=list)
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_auth_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    idle_expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + IDLE_WINDOW)
    absolute_expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + ABSOLUTE_WINDOW)
    session_version: int = 1
    revoked: bool = False
    revoke_reason: Optional[str] = None


class SessionStore:
    """Thread-safe in-memory session store (alpha)."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._lock = threading.RLock()
        self.audit_entries: list[dict] = []

    def _log(self, action: str, session: Optional[SessionRecord], detail: str = "") -> None:
        self.audit_entries.append({
            "audit_id": str(uuid.uuid4()),
            "action": action,
            "user_id": session.user_id if session else None,
            "session_id": session.session_id if session else None,
            "practice_id": session.active_practice_id if session else None,
            "detail": detail,
            "at": datetime.now(timezone.utc).isoformat(),
        })

    def create(
        self,
        user_id: str,
        assurance: str = "medium",
        auth_methods: Optional[list[str]] = None,
        practice_id: Optional[str] = None,
        membership_id: Optional[str] = None,
        roles: Optional[list[str]] = None,
    ) -> SessionRecord:
        token = secrets.token_urlsafe(32)
        record = SessionRecord(
            session_id=token,
            user_id=user_id,
            csrf_token=secrets.token_urlsafe(24),
            assurance=assurance,
            auth_methods=auth_methods or ["pwd", "mock_mfa"],
            active_practice_id=practice_id,
            active_membership_id=membership_id,
            roles=list(roles or []),
        )
        with self._lock:
            self._sessions[token] = record
            self._log("SESSION_CREATE", record, f"assurance={assurance}")
            supabase_store.upsert("application_sessions", _to_row(record), "session_id")
        return record

    def _restore(self, token: str) -> Optional[SessionRecord]:
        rows = supabase_store.select("application_sessions", filters={"session_id": f"eq.{token}"}, limit=1)
        if not rows:
            return None
        record = _from_row(rows[0])
        with self._lock:
            self._sessions[token] = record
        return record

    def get(self, token: Optional[str], *, touch: bool = True) -> SessionRecord:
        if not token:
            raise AuthError("NO_SESSION", 401, "No session supplied")
        with self._lock:
            record = self._sessions.get(token)
        if record is None:
            record = self._restore(token)
        if record is None:
            raise AuthError("UNKNOWN_SESSION", 401, "Session is not recognised")
        now = datetime.now(timezone.utc)
        if record.revoked:
            raise AuthError("SESSION_REVOKED", 401, "Session has been revoked")
        if now >= record.absolute_expires_at:
            record.revoked = True
            self._log("SESSION_ABSOLUTE_EXPIRY", record)
            raise AuthError("SESSION_EXPIRED", 401, "Session has expired")
        if now >= record.idle_expires_at:
            record.revoked = True
            self._log("SESSION_IDLE_EXPIRY", record)
            raise AuthError("SESSION_IDLE_TIMEOUT", 401, "Session timed out")
        if touch:
            record.last_activity_at = now
            record.idle_expires_at = now + IDLE_WINDOW
        return record

    def require_step_up(self, record: SessionRecord) -> None:
        now = datetime.now(timezone.utc)
        if now - record.last_auth_at > STEP_UP_WINDOW or record.assurance != "high":
            raise AuthError("REAUTH_REQUIRED", 401, "Step-up authentication required")

    def step_up(self, token: str) -> SessionRecord:
        with self._lock:
            record = self.get(token, touch=True)
            record.last_auth_at = datetime.now(timezone.utc)
            record.assurance = "high"
            if "phishing_resistant" not in record.auth_methods:
                record.auth_methods.append("phishing_resistant")
            self._log("SESSION_STEP_UP", record)
            supabase_store.update("application_sessions", {"session_id": f"eq.{record.session_id}"}, {
                "assurance": record.assurance,
                "last_auth_at": record.last_auth_at.isoformat(),
                "auth_methods": json.dumps(record.auth_methods),
            })
            return record

    def select_practice(
        self, token: str, practice_id: str, expected_version: Optional[int]
    ) -> SessionRecord:
        with self._lock:
            record = self.get(token, touch=True)
            if expected_version is not None and expected_version != record.session_version:
                raise AuthError("STALE_SESSION_VERSION", 409, "Practice context changed")
            record.active_practice_id = practice_id
            record.active_membership_id = f"membership-{practice_id}"
            record.roles = ["practice_member"]
            record.session_version += 1
            self._log("PRACTICE_CONTEXT_SELECT", record, practice_id)
            supabase_store.update("application_sessions", {"session_id": f"eq.{record.session_id}"}, {
                "active_practice_id": record.active_practice_id,
                "active_membership_id": record.active_membership_id,
                "roles": json.dumps(record.roles),
                "session_version": record.session_version,
            })
            return record

    def revoke(self, token: str, reason: str = "user_logout") -> None:
        with self._lock:
            record = self._sessions.get(token)
            if record is None:
                return
            record.revoked = True
            record.revoke_reason = reason
            self._log("SESSION_REVOKE", record, reason)
            supabase_store.update("application_sessions", {"session_id": f"eq.{token}"}, {
                "revoked": True, "revoke_reason": reason,
            })

    def revoke_user_sessions(self, user_id: str, reason: str = "staff_deactivation") -> int:
        with self._lock:
            count = 0
            for record in self._sessions.values():
                if record.user_id == user_id and not record.revoked:
                    record.revoked = True
                    record.revoke_reason = reason
                    self._log("SESSION_REVOKE", record, reason)
                    supabase_store.update("application_sessions", {"session_id": f"eq.{record.session_id}"}, {
                        "revoked": True, "revoke_reason": reason,
                    })
                    count += 1
            return count

    def sessions_for_user(self, user_id: str) -> list[SessionRecord]:
        with self._lock:
            return [r for r in self._sessions.values() if r.user_id == user_id]

    def principal(self, record: SessionRecord) -> dict:
        return {
            "user_id": record.user_id,
            "assurance": record.assurance,
            "auth_methods": list(record.auth_methods),
            "active_practice": record.active_practice_id,
            "active_membership": record.active_membership_id,
            "permitted_roles": list(record.roles),
            "session_version": record.session_version,
            "idle_expires_at": record.idle_expires_at.isoformat(),
            "absolute_expires_at": record.absolute_expires_at.isoformat(),
            "safe_prompts": ["practice_phone", "emergency_text"],
        }


_TIMESTAMP_FIELDS = (
    "issued_at", "last_activity_at", "last_auth_at", "idle_expires_at", "absolute_expires_at"
)


def _to_row(record: SessionRecord) -> dict:
    row = asdict(record)
    for key in _TIMESTAMP_FIELDS:
        value = row.get(key)
        row[key] = value.isoformat() if isinstance(value, datetime) else value
    row["auth_methods"] = json.dumps(row["auth_methods"])
    row["roles"] = json.dumps(row["roles"])
    return row


def _from_row(row: dict) -> SessionRecord:
    def dt(key):
        value = row.get(key)
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value) if value else datetime.now(timezone.utc)

    def arr(key):
        value = row.get(key) or "[]"
        return json.loads(value) if isinstance(value, str) else value

    return SessionRecord(
        session_id=row["session_id"], user_id=row["user_id"], csrf_token=row["csrf_token"],
        assurance=row.get("assurance", "medium"), auth_methods=arr("auth_methods"),
        active_practice_id=row.get("active_practice_id"),
        active_membership_id=row.get("active_membership_id"), roles=arr("roles"),
        issued_at=dt("issued_at"), last_activity_at=dt("last_activity_at"),
        last_auth_at=dt("last_auth_at"), idle_expires_at=dt("idle_expires_at"),
        absolute_expires_at=dt("absolute_expires_at"),
        session_version=int(row.get("session_version") or 1),
        revoked=bool(row.get("revoked")), revoke_reason=row.get("revoke_reason"),
    )


session_store = SessionStore()
