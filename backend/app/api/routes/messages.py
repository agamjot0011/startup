"""In-app messaging endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.routes.auth import current_session
from app.services.authz_service import AuthzError, authorize
from app.services.messaging_service import MessagingError, messaging_service
from app.services.session_service import SessionRecord

router = APIRouter(tags=["Messages"])


class PublishRequest(BaseModel):
    body: str


def _scope(session: SessionRecord, patient_id: str, action: str):
    try:
        authorize(
            session, "patient", action,
            practice_id=session.active_practice_id,
            patient_id=patient_id, subject_patient_id=patient_id,
            relationship_verified=True, consent_active=True,
        )
    except AuthzError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


@router.post("/v1/patients/{patient_id}/messages")
def publish(
    patient_id: str, payload: PublishRequest, session: SessionRecord = Depends(current_session)
):
    try:
        authorize(session, "card", "acknowledge", practice_id=session.active_practice_id)
        message = messaging_service.publish(
            session.active_practice_id, patient_id, payload.body, session
        )
    except (AuthzError, MessagingError) as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return message.public()


@router.get("/v1/patients/{patient_id}/messages")
def list_messages(patient_id: str, session: SessionRecord = Depends(current_session)):
    _scope(session, patient_id, "read_own")
    return {"messages": [m.public() for m in messaging_service.for_patient(
        session.active_practice_id, patient_id
    )]}


@router.get("/v1/messages/{message_id}")
def get_message(message_id: str, session: SessionRecord = Depends(current_session)):
    try:
        message = messaging_service.get(message_id)
    except MessagingError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    _scope(session, message.patient_id, "read_own")
    return message.public()


@router.post("/v1/messages/{message_id}/views")
def view_message(message_id: str, session: SessionRecord = Depends(current_session)):
    try:
        message = messaging_service.get(message_id)
    except MessagingError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    _scope(session, message.patient_id, "read_own")
    return messaging_service.view(message_id, session)
