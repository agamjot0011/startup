"""Visit brief endpoints — canonical /v1/visit-briefs family."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.routes.auth import current_session
from app.services.authz_service import AuthzError, authorize
from app.services.brief_service import BriefError, brief_service
from app.services.session_service import SessionRecord

router = APIRouter(tags=["Visit Briefs"])


class GenerateBriefRequest(BaseModel):
    appointment_id: str
    patient_id: str
    events: list[dict] = []


class SignBriefRequest(BaseModel):
    attestation: str
    expected_row_version: int


class SupersedeRequest(BaseModel):
    reason: str
    events: list[dict]


@router.post("/v1/visit-briefs")
def generate_brief(payload: GenerateBriefRequest, session: SessionRecord = Depends(current_session)):
    try:
        authorize(session, "patient", "read_care", practice_id=session.active_practice_id)
        brief = brief_service.generate(
            appointment_id=payload.appointment_id,
            practice_id=session.active_practice_id,
            patient_id=payload.patient_id,
            events=payload.events,
            actor=session,
        )
    except (AuthzError, BriefError) as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return brief.public()


@router.get("/v1/visit-briefs/{appointment_id}")
def get_brief(appointment_id: str, session: SessionRecord = Depends(current_session)):
    brief = brief_service.by_appointment(appointment_id)
    if brief is None:
        raise HTTPException(status_code=404, detail={"code": "BRIEF_NOT_FOUND"})
    return brief.public()


@router.post("/v1/visit-briefs/{brief_id}/signatures")
def sign_brief(
    brief_id: str, payload: SignBriefRequest, session: SessionRecord = Depends(current_session)
):
    try:
        authorize(session, "brief", "sign", practice_id=session.active_practice_id)
        signature = brief_service.sign(
            brief_id, actor=session,
            attestation=payload.attestation,
            expected_row_version=payload.expected_row_version,
        )
    except (AuthzError, BriefError) as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return {
        "signature_id": signature.signature_id,
        "brief_id": signature.brief_id,
        "signed_at": signature.signed_at,
        "snapshot_hash": signature.snapshot_hash,
        "assurance": signature.assurance,
    }


@router.get("/v1/visit-briefs/{brief_id}/signatures/{signature_id}")
def get_signature(brief_id: str, signature_id: str, session: SessionRecord = Depends(current_session)):
    try:
        signature = brief_service.get_signature(signature_id)
    except BriefError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    if signature.brief_id != brief_id:
        raise HTTPException(status_code=404, detail={"code": "SIGNATURE_NOT_FOUND"})
    return {
        "signature_id": signature.signature_id,
        "brief_id": signature.brief_id,
        "snapshot_hash": signature.snapshot_hash,
        "attestation": signature.attestation,
        "signed_at": signature.signed_at,
    }


@router.post("/v1/visit-briefs/{brief_id}/supersessions")
def supersede_brief(
    brief_id: str, payload: SupersedeRequest, session: SessionRecord = Depends(current_session)
):
    try:
        authorize(session, "brief", "sign", practice_id=session.active_practice_id)
        replacement = brief_service.supersede(
            brief_id, reason=payload.reason, events=payload.events, actor=session
        )
    except (AuthzError, BriefError) as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return {
        "supersedes": brief_id,
        "replacement_brief_id": replacement.brief_id,
        "row_version": replacement.row_version,
    }
