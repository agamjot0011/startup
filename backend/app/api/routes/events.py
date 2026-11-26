"""Append-only event ledger endpoints (handbook overview step 11)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.api.routes.auth import current_session
from app.services.authz_service import AuthzError, require
from app.services.event_ledger import event_ledger
from app.services.session_service import AuthError, SessionRecord, session_store

router = APIRouter(tags=["Events"])


class AppendEventRequest(BaseModel):
    patient_id: str
    event_type: str
    source_type: str
    source_id: str
    payload: dict = {}


class CorrectEventRequest(BaseModel):
    payload: dict
    reason: str


@router.post("/v1/events")
def append_event(
    payload: AppendEventRequest,
    session: SessionRecord = Depends(current_session),
    scope: dict = Depends(require("patient", "read_care")),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    request = payload.model_dump()
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key is required")

    def work() -> dict:
        event = event_ledger.append(
            practice_id=session.active_practice_id,
            patient_id=payload.patient_id,
            event_type=payload.event_type,
            source_type=payload.source_type,
            source_id=payload.source_id,
            payload=payload.payload,
            actor_user_id=session.user_id,
        )
        return {"event_id": event.event_id, "event_hash": event.event_hash, "recorded_at": event.recorded_at}

    try:
        result, replayed = event_ledger.execute_idempotent(
            "event_append", idempotency_key, request, work
        )
    except AuthzError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return {**result, "replayed": replayed}


@router.post("/v1/events/{event_id}/corrections")
def correct_event(
    event_id: str,
    payload: CorrectEventRequest,
    session: SessionRecord = Depends(current_session),
    _scope: dict = Depends(require("patient", "read_care")),
):
    try:
        session_store.require_step_up(session)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    try:
        event = event_ledger.correct(
            event_id, payload=payload.payload, reason=payload.reason, actor_user_id=session.user_id
        )
    except AuthzError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return {
        "correction_event_id": event.event_id,
        "corrects": event_id,
        "event_hash": event.event_hash,
    }


@router.get("/v1/events/{event_id}/reconstruction")
def reconstruct_event(
    event_id: str, _scope: dict = Depends(require("patient", "read_care"))
):
    try:
        return event_ledger.reconstruct(event_id)
    except AuthzError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


@router.get("/v1/events/ledger/verify")
def verify_ledger(_scope: dict = Depends(require("audit", "read"))):
    return {"verified": event_ledger.verify(), "event_count": len(event_ledger._order)}


@router.get("/v1/outbox/pending")
def pending_outbox(_scope: dict = Depends(require("audit", "read"))):
    messages = event_ledger.pending_outbox()
    return {"count": len(messages), "messages": [m.outbox_id for m in messages]}


@router.post("/v1/outbox/dispatch")
def dispatch_outbox(_scope: dict = Depends(require("audit", "read"))):
    return {"dispatched": event_ledger.dispatch_outbox()}
