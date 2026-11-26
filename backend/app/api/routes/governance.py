"""Rule and content governance endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.routes.auth import current_session
from app.services.authz_service import AuthzError, authorize
from app.services.governance_service import GovernanceError, governance_service
from app.services.session_service import SessionRecord

router = APIRouter(tags=["Governance"])


class CreateVersionRequest(BaseModel):
    body: dict
    replaces: str | None = None


class ActivateRequest(BaseModel):
    effective_from: str | None = None


class WithdrawRequest(BaseModel):
    reason: str


def _manager(session: SessionRecord):
    try:
        authorize(session, "operations", "read", practice_id=session.active_practice_id)
    except AuthzError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


@router.post("/v1/governance/{kind}/versions")
def create(kind: str, payload: CreateVersionRequest, session: SessionRecord = Depends(current_session)):
    _manager(session)
    try:
        version = governance_service.create_version(
            kind, session.active_practice_id, payload.body, session, payload.replaces
        )
    except GovernanceError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return version.public()


@router.post("/v1/governance/versions/{version_id}/submit")
def submit(version_id: str, session: SessionRecord = Depends(current_session)):
    _manager(session)
    try:
        return governance_service.submit(version_id, session).public()
    except GovernanceError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


@router.post("/v1/governance/versions/{version_id}/approve")
def approve(version_id: str, session: SessionRecord = Depends(current_session)):
    try:
        version = governance_service.get(version_id)
        authorize(session, "rule" if version.kind == "rule" else "content", "approve",
                  practice_id=session.active_practice_id)
        return governance_service.approve(version_id, session).public()
    except (AuthzError, GovernanceError) as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


@router.post("/v1/governance/versions/{version_id}/activate")
def activate(
    version_id: str, payload: ActivateRequest, session: SessionRecord = Depends(current_session)
):
    _manager(session)
    try:
        return governance_service.activate(version_id, session, payload.effective_from).public()
    except GovernanceError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


@router.post("/v1/governance/versions/{version_id}/withdraw")
def withdraw(
    version_id: str, payload: WithdrawRequest, session: SessionRecord = Depends(current_session)
):
    _manager(session)
    try:
        return governance_service.withdraw(version_id, payload.reason, session).public()
    except GovernanceError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


@router.get("/v1/governance/versions")
def versions(kind: str | None = None, session: SessionRecord = Depends(current_session)):
    _manager(session)
    return {"versions": [v.public() for v in governance_service.active_versions(kind)]}
