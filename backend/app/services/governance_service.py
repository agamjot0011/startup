"""Governed rule and content version lifecycle.

Handbook detailed steps 12 and 13. An item has immutable versions; editing a
version invalidates its approval. Authors cannot approve their own drafts.
Only approved versions can be activated, and safety withdrawal is available
without editing the withdrawn bytes.
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.services.authz_service import AuthzError
from app.services.event_ledger import event_ledger
from app.services.session_service import SessionRecord

DRAFT = "DRAFT"
SUBMITTED = "SUBMITTED"
APPROVED = "APPROVED"
ACTIVE = "ACTIVE"
WITHDRAWN = "WITHDRAWN"

FORBIDDEN_RULE_OPERATORS = {"ai", "infer", "guess", "auto_urgency", "model_score"}


class GovernanceError(Exception):
    def __init__(self, code: str, status: int = 400, message: str = "") -> None:
        self.code, self.status = code, status
        self.message = message or code
        super().__init__(self.message)


def _hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@dataclass
class Version:
    version_id: str
    item_id: str
    kind: str
    body: dict
    checksum: str
    state: str
    author_user_id: str
    created_at: str
    approver_user_id: Optional[str] = None
    approved_at: Optional[str] = None
    activated_at: Optional[str] = None
    withdrawn_at: Optional[str] = None
    withdrawal_reason: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    locale: str = "en"

    def public(self) -> dict:
        return {
            "version_id": self.version_id, "item_id": self.item_id, "kind": self.kind,
            "checksum": self.checksum, "state": self.state,
            "author_user_id": self.author_user_id, "approver_user_id": self.approver_user_id,
            "approved_at": self.approved_at, "activated_at": self.activated_at,
            "withdrawn_at": self.withdrawn_at, "withdrawal_reason": self.withdrawal_reason,
            "effective_from": self.effective_from, "effective_to": self.effective_to,
            "locale": self.locale,
        }


class GovernanceService:
    def __init__(self) -> None:
        self._items: dict[str, list[Version]] = {}
        self._versions: dict[str, Version] = {}
        self._lock = threading.RLock()

    @staticmethod
    def validate_body(kind: str, body: dict) -> None:
        if kind == "rule":
            operators = body.get("operators", [])
            found = [op for op in operators if str(op).lower() in FORBIDDEN_RULE_OPERATORS]
            if found:
                raise GovernanceError("FORBIDDEN_OPERATOR", 400, ",".join(found))
            if not body.get("name") or not body.get("when"):
                raise GovernanceError("RULE_FIELDS_REQUIRED", 400)
        else:
            if not body.get("title") or not body.get("text"):
                raise GovernanceError("CONTENT_FIELDS_REQUIRED", 400)

    def create_version(
        self, kind: str, practice_id: str, body: dict, author: SessionRecord,
        replaces: Optional[str] = None,
    ) -> Version:
        self.validate_body(kind, body)
        with self._lock:
            item_id = str(uuid.uuid4())
            version = Version(
                version_id=str(uuid.uuid4()), item_id=item_id, kind=kind,
                body=dict(body), checksum=_hash(body), state=DRAFT,
                author_user_id=author.user_id,
                created_at=datetime.now(timezone.utc).isoformat(),
                locale=body.get("locale", "en"),
            )
            self._items.setdefault(item_id, []).append(version)
            self._versions[version.version_id] = version
            if replaces and replaces in self._versions:
                previous = self._versions[replaces]
                if previous.state == ACTIVE:
                    previous.state = WITHDRAWN
                    previous.withdrawal_reason = "replaced by new version"
            event_ledger.append(
                practice_id=practice_id, patient_id="governance",
                event_type=f"{kind}_version_created.v1", source_type="governance",
                source_id=version.version_id, payload={"item_id": item_id, "checksum": version.checksum},
                actor_user_id=author.user_id,
            )
            return version

    def get(self, version_id: str) -> Version:
        version = self._versions.get(version_id)
        if version is None:
            raise GovernanceError("VERSION_NOT_FOUND", 404)
        return version

    def submit(self, version_id: str, author: SessionRecord) -> Version:
        with self._lock:
            version = self.get(version_id)
            if version.state != DRAFT:
                raise GovernanceError("INVALID_STATE", 409, version.state)
            version.state = SUBMITTED
            return version

    def approve(self, version_id: str, approver: SessionRecord) -> Version:
        with self._lock:
            version = self.get(version_id)
            if version.state != SUBMITTED:
                raise GovernanceError("INVALID_STATE", 409, version.state)
            if approver.user_id == version.author_user_id:
                raise GovernanceError("AUTHOR_CANNOT_APPROVE", 403)
            if approver.roles and not ({"orthodontist", "practice_manager"} & set(approver.roles)):
                raise AuthzError("NO_PERMITTED_ROLE", 403)
            version.state = APPROVED
            version.approver_user_id = approver.user_id
            version.approved_at = datetime.now(timezone.utc).isoformat()
            return version

    def activate(self, version_id: str, actor: SessionRecord, effective_from: Optional[str] = None) -> Version:
        with self._lock:
            version = self.get(version_id)
            if version.state != APPROVED:
                raise GovernanceError("APPROVAL_REQUIRED", 409)
            if _hash(version.body) != version.checksum:
                version.state = DRAFT
                raise GovernanceError("APPROVAL_INVALIDATED", 409)
            version.state = ACTIVE
            version.activated_at = datetime.now(timezone.utc).isoformat()
            version.effective_from = effective_from or version.activated_at
            for other in self._items[version.item_id]:
                if other.version_id != version_id and other.state == ACTIVE:
                    other.state = WITHDRAWN
                    other.withdrawal_reason = "superseded"
            return version

    def withdraw(self, version_id: str, reason: str, actor: SessionRecord) -> Version:
        if not reason.strip():
            raise GovernanceError("WITHDRAWAL_REASON_REQUIRED", 400)
        with self._lock:
            version = self.get(version_id)
            version.state = WITHDRAWN
            version.withdrawn_at = datetime.now(timezone.utc).isoformat()
            version.withdrawal_reason = reason
            return version

    def active_versions(self, kind: Optional[str] = None) -> list[Version]:
        return [
            v for v in self._versions.values()
            if v.state == ACTIVE and (kind is None or v.kind == kind)
        ]


governance_service = GovernanceService()
