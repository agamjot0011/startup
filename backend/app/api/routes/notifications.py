"""Notification pipeline endpoints — provider gates, PHI blocks and health."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.routes.auth import current_session
from app.services.authz_service import AuthzError, authorize
from app.services.notification_service import ALLOWED_TEMPLATES, NotificationError, notification_service
from app.services.session_service import SessionRecord, session_store

router = APIRouter(tags=["Notifications"])


class EnqueueRequest(BaseModel):
    site_id: str
    patient_id: str
    template_id: str
    channel: str
    role: str = "clinical_assistant"
    urgent: bool = False


class ProviderRequest(BaseModel):
    site_id: str
    sms_enabled: bool = False
    email_enabled: bool = False


def _manager(session: SessionRecord):
    try:
        authorize(session, "operations", "read", practice_id=session.active_practice_id)
        session_store.require_step_up(session)
    except (AuthzError, Exception) as exc:
        code = getattr(exc, "code", "REAUTH_REQUIRED")
        status = getattr(exc, "status", 401)
        raise HTTPException(status_code=status, detail={"code": code, "message": str(exc)})


@router.post("/v1/notifications/commands")
def enqueue(payload: EnqueueRequest, session: SessionRecord = Depends(current_session)):
    try:
        authorize(session, "operations", "read", practice_id=session.active_practice_id)
        command = notification_service.enqueue(
            practice_id=session.active_practice_id,
            site_id=payload.site_id, patient_id=payload.patient_id,
            template_id=payload.template_id, channel=payload.channel,
            role=payload.role, urgent=payload.urgent,
        )
    except (AuthzError, NotificationError) as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})
    return {
        "command_id": command.command_id,
        "status": command.status,
        "channel": command.channel,
        "not_before": command.not_before,
        "blocked_reason": command.blocked_reason,
    }


@router.post("/v1/notifications/provider-config")
def configure_provider(payload: ProviderRequest, session: SessionRecord = Depends(current_session)):
    _manager(session)
    notification_service.configure_provider(payload.site_id, payload.sms_enabled, payload.email_enabled)
    return {"site_id": payload.site_id, "sms": payload.sms_enabled, "email": payload.email_enabled}


@router.get("/v1/notifications/health")
def notification_health(session: SessionRecord = Depends(current_session)):
    _manager(session)
    return {"status_counts": notification_service.health(), "templates": sorted(ALLOWED_TEMPLATES)}


@router.post("/v1/notifications/dispatch")
def dispatch(session: SessionRecord = Depends(current_session)):
    _manager(session)
    return notification_service.dispatch_pending()
