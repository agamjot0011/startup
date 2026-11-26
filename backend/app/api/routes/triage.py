"""Human triage endpoints — no machine-generated urgency."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.routes.auth import current_session
from app.services.authz_service import AuthzError, authorize
from app.services.session_service import SessionRecord
from app.services.triage_service import APPROVED_INSTRUCTIONS, URGENCIES, TriageError, triage_service

router = APIRouter(tags=["Problem Reports"])


class SubmitReportRequest(BaseModel):
    title: str
    description: str
    photo_attached: bool = False


class TriageRequest(BaseModel):
    urgency: str
    approved_instruction: str


@router.post("/v1/reports/{patient_id}/reports")
def submit_report(
    patient_id: str,
    payload: SubmitReportRequest,
    session: SessionRecord = Depends(current_session),
):
    try:
        authorize(
            session, "report", "create",
            practice_id=session.active_practice_id,
            patient_id=patient_id, subject_patient_id=patient_id,
            relationship_verified=True, consent_active=True,
        )
        report = triage_service.submit(
            practice_id=session.active_practice_id,
            patient_id=patient_id,
            title=payload.title,
            description=payload.description,
            actor=session,
            photo_attached=payload.photo_attached,
        )
    except (AuthzError, TriageError) as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return {
        "report_id": report.report_id,
        "status": report.status,
        "received_at": report.received_at,
        "triage_card_id": report.triage_card_id,
        "practice_contact": {"phone": "(555) 010-2200", "emergency_wording": "Use the safe route"},
    }


@router.get("/v1/reports/{report_id}")
def get_report(report_id: str, session: SessionRecord = Depends(current_session)):
    try:
        report = triage_service.get(report_id)
    except TriageError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return {
        "report_id": report.report_id,
        "status": report.status,
        "urgency": report.urgency,
        "approved_instruction": APPROVED_INSTRUCTIONS.get(report.approved_instruction or ""),
        "received_at": report.received_at,
    }


@router.post("/v1/problem-reports/{report_id}/triage")
def triage_report(
    report_id: str,
    payload: TriageRequest,
    session: SessionRecord = Depends(current_session),
):
    try:
        authorize(session, "report", "triage", practice_id=session.active_practice_id)
        result = triage_service.triage(
            report_id,
            urgency=payload.urgency,
            approved_instruction=payload.approved_instruction,
            actor=session,
        )
    except (AuthzError, TriageError) as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return result
