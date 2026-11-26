"""Metric fact endpoints — manager-only, with independent recomputation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.routes.auth import current_session
from app.services.authz_service import AuthzError, authorize
from app.services.metrics_service import metrics_service
from app.services.session_service import SessionRecord

router = APIRouter(tags=["Metrics"])


def _manager(session: SessionRecord):
    try:
        authorize(session, "operations", "read", practice_id=session.active_practice_id)
    except AuthzError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


@router.get("/v1/metrics")
def list_metrics(session: SessionRecord = Depends(current_session)):
    _manager(session)
    return {
        "facts": [f.public() for f in metrics_service.facts()],
        "provisional_baseline": True,
    }


@router.get("/v1/metrics/verify")
def verify_metrics(session: SessionRecord = Depends(current_session)):
    _manager(session)
    return metrics_service.verify()


@router.get("/v1/metrics/{metric_id}")
def get_metric(metric_id: str, session: SessionRecord = Depends(current_session)):
    _manager(session)
    for fact in metrics_service.facts():
        if fact.metric_id == metric_id:
            return fact.public()
    raise HTTPException(status_code=404, detail={"code": "METRIC_NOT_FOUND"})
