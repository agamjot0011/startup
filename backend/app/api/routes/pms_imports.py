"""PMS import endpoints — quarantine, dry run, commit and correction."""

from __future__ import annotations

import base64
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.routes.auth import current_session
from app.services.authz_service import AuthzError, authorize
from app.services.pms_service import ImportError, pms_service
from app.services.session_service import SessionRecord, session_store

router = APIRouter(tags=["Imports"])


class UploadRequest(BaseModel):
    filename: str
    content_base64: str


class DryRunRequest(BaseModel):
    mapping: Optional[dict] = None


class CorrectionRequest(BaseModel):
    reason: str


def _manager(session: SessionRecord):
    try:
        authorize(session, "operations", "read", practice_id=session.active_practice_id)
        session_store.require_step_up(session)
    except Exception as exc:
        code = getattr(exc, "code", "REAUTH_REQUIRED")
        raise HTTPException(status_code=getattr(exc, "status", 401), detail={"code": code, "message": str(exc)})


@router.post("/v1/pms-imports/packages")
def upload(payload: UploadRequest, session: SessionRecord = Depends(current_session)):
    _manager(session)
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
        batch = pms_service.quarantine(session.active_practice_id, payload.filename, content)
    except (ImportError, ValueError) as exc:
        raise HTTPException(status_code=getattr(exc, "status", 400), detail={"code": getattr(exc, "code", "INVALID_PACKAGE"), "message": str(exc)})
    return batch.public()


@router.get("/v1/pms-imports/{import_id}")
def get_import(import_id: str, session: SessionRecord = Depends(current_session)):
    try:
        authorize(session, "operations", "read", practice_id=session.active_practice_id)
        batch = pms_service.get(import_id)
    except (AuthzError, ImportError) as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return batch.public()


@router.post("/v1/pms-imports/{import_id}/dry-run")
def dry_run(
    import_id: str, payload: DryRunRequest, session: SessionRecord = Depends(current_session)
):
    _manager(session)
    try:
        return pms_service.dry_run(import_id, payload.mapping)
    except ImportError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


@router.post("/v1/pms-imports/{import_id}/commit")
def commit(import_id: str, session: SessionRecord = Depends(current_session)):
    _manager(session)
    try:
        return pms_service.commit(import_id, session.user_id)
    except ImportError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


@router.post("/v1/pms-imports/{import_id}/corrections")
def correct(
    import_id: str, payload: CorrectionRequest, session: SessionRecord = Depends(current_session)
):
    _manager(session)
    try:
        return pms_service.compensating_correction(import_id, payload.reason, session.user_id)
    except ImportError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
