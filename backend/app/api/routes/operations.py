"""Assistant chair card and front-desk booking/promise endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.routes.auth import current_session
from app.services.authz_service import AuthzError, authorize
from app.services.operations_service import CHECKLIST_VERSION, OperationsError, operations_service
from app.services.session_service import SessionRecord

router = APIRouter(tags=["Staff Operations"])


class CaptureRequest(BaseModel):
    appointment_id: str
    capture_type: str
    content: str
    checklist_version: str = CHECKLIST_VERSION


class PromiseRequest(BaseModel):
    text: str
    owner_membership_id: str
    due_phrase: str


@router.get("/v1/staff/assistant/today")
def assistant_today(session: SessionRecord = Depends(current_session)):
    try:
        authorize(session, "card", "read", practice_id=session.active_practice_id)
    except AuthzError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return {
        "practice_id": session.active_practice_id,
        "appointments": [operations_service.seed_appointment().appointment_id],
        "checklist_version": CHECKLIST_VERSION,
    }


@router.get("/v1/staff/chair-cards/{appointment_id}")
def chair_card(appointment_id: str, session: SessionRecord = Depends(current_session)):
    try:
        authorize(session, "patient", "read_care", practice_id=session.active_practice_id)
        return operations_service.chair_card(appointment_id)
    except AuthzError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


@router.post("/v1/patients/{patient_id}/chairside-captures")
def capture_chairside(
    patient_id: str, payload: CaptureRequest, session: SessionRecord = Depends(current_session)
):
    try:
        authorize(session, "patient", "read_care", practice_id=session.active_practice_id)
        capture = operations_service.capture(
            payload.appointment_id, patient_id, payload.capture_type,
            payload.content, session, payload.checklist_version,
        )
    except (AuthzError, OperationsError) as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return capture.public()


@router.get("/v1/operations/front-desk-daily")
def front_desk_daily(session: SessionRecord = Depends(current_session)):
    try:
        authorize(session, "booking", "manage", practice_id=session.active_practice_id)
    except AuthzError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    appointment = operations_service.seed_appointment()
    return {
        "date": "2026-11-27",
        "appointments": [{
            "appointment_id": appointment.appointment_id,
            "patient_id": appointment.patient_id,
            "scheduled_at": appointment.scheduled_at,
            "reason": appointment.reason,
            "status": appointment.status,
        }],
    }


@router.post("/v1/patients/{patient_id}/promises")
def make_promise(
    patient_id: str, payload: PromiseRequest, session: SessionRecord = Depends(current_session)
):
    try:
        authorize(session, "promise", "manage", practice_id=session.active_practice_id)
        promise = operations_service.make_promise(
            session.active_practice_id, patient_id, payload.text,
            payload.owner_membership_id, payload.due_phrase, session,
        )
    except (AuthzError, OperationsError) as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return {
        "promise_id": promise.promise_id,
        "patient_id": promise.patient_id,
        "due_at": promise.due_at,
        "state": promise.state,
    }


@router.get("/v1/operations/promises")
def list_promises(session: SessionRecord = Depends(current_session)):
    try:
        authorize(session, "promise", "manage", practice_id=session.active_practice_id)
    except AuthzError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    promises = operations_service.promises(session.active_practice_id)
    return {"count": len(promises), "promises": [p.__dict__ for p in promises]}


@router.get("/v1/promises/{promise_id}")
def get_promise(promise_id: str, session: SessionRecord = Depends(current_session)):
    try:
        authorize(session, "promise", "manage", practice_id=session.active_practice_id)
        promise = operations_service.promise(promise_id)
    except (AuthzError, OperationsError) as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return promise.__dict__
