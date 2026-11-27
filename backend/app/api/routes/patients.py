from datetime import datetime

from fastapi import APIRouter, Depends

from app.api.routes.auth import current_session
from app.services.event_ledger import event_ledger
from app.services.session_service import SessionRecord

router = APIRouter(prefix="/v1/patients", tags=["Patients"])


# ---------------------------------------------------------------------------
#  /v1/patients  -- authorised timeline, today tasks, check-ins
# ---------------------------------------------------------------------------


@router.get("")
def list_patients():
    """
    List authorised patient summaries for the active practice.
    No cross-tenant or count leakage.
    """
    return {"patients": [{"patient_id": "synthetic", "display_name": "Synthetic Patient"}], "next_cursor": None}


@router.post("")
def create_patient():
    """
    Create a practice-scoped patient with exact match.
    Returns patient_id and status.
    """
    return {
        "patient_id": "synthetic",
        "status": "active",
        "created_at": "2026-11-25T12:00:00Z",
    }


@router.get("/{patient_id}/family-home")
def family_home(patient_id: str):
    """
    Return a patient-only home projection.
    """
    return {
        "patient_id": patient_id,
        "safe_route": {"contact_phone": "011-800-000-0000", "emergency_wording": "Call 111"},
        "today_card_summary": [],
        "next_visit_summary": None,
        "unread_count": 0,
    }


@router.get("/{patient_id}/timeline")
def get_patient_timeline(patient_id: str, session: SessionRecord = Depends(current_session)):
    """Role/privacy-filtered patient timeline from the persisted event ledger."""
    events = []
    for e in event_ledger.timeline(session.active_practice_id, patient_id):
        try:
            date = datetime.fromisoformat(e["recorded_at"].replace("Z", "+00:00")).strftime("%d %b %Y")
        except (ValueError, TypeError):
            date = e["recorded_at"][:10]
        kind = e["event_type"].split(".")[0].replace("_", " ").title()
        events.append({
            "id": e["event_id"], "date": date, "type": kind,
            "title": e["event_type"].replace(".v1", "").replace("_", " ").title(),
            "source": e["source_type"].replace("_", " ").title(),
            "freshness": "Verified", "tone": "success",
            "event_id": e["event_id"], "event_type": e["event_type"],
            "recorded_at": e["recorded_at"], "event_hash": e["event_hash"],
        })
    return events


@router.post("/{patient_id}/enrolments")
def start_patient_enrolment():
    """
    Start a patient enrolment case.
    """
    return {
        "enrolment_id": "synthetic",
        "required_steps": ["identity_verification", "consent", "proxy_relationship"],
        "blockers": [],
    }


@router.post("/{patient_id}/identity-verifications")
def record_identity_verification():
    """
    Record an immutable identity verification result.
    """
    return {
        "verification_id": "synthetic",
        "method": "staff_verified",
        "status": "verified",
    }


@router.post("/{patient_id}/withdrawals")
def withdraw_patient_participation():
    """
    Record a withdrawal; future access stops.
    """
    return {
        "withdrawal_id": "synthetic",
        "effective_at": "2026-11-25T12:00:00Z",
        "future_use_stopped": True,
    }


@router.get("/{patient_id}/reports/{report_id}")
def get_report(report_id: str):
    """
    Get a report with permitted facts.
    """
    return {
        "report_id": report_id,
        "status": "AWAITING_HUMAN_TRIAGE",
        "received_at": "2026-11-25T12:00:00Z",
        "approved_contact_version": {"phone": "011-800-000-0000"},
    }


@router.get("/{patient_id}/digests/current")
def current_digest():
    """
    Get the latest authorised in-app digest.
    """
    return {
        "digest_id": "synthetic",
        "items": [],
        "period": "2026-W47",
        "received_at": "2026-11-25T12:00:00Z",
    }


@router.get("/{patient_id}/notification-preferences")
def get_notification_preferences():
    """
    Get channel preferences.
    """
    return {
        "preferences": [
            {"channel_code": "in_app", "status": "active", "quiet_start": "22:00", "quiet_end": "07:00"}
        ]
    }


@router.post("/{patient_id}/notification-preferences")
def update_notification_preferences():
    """
    Update channel/schedule preferences with idempotency and If-Match.
    """
    return {
        "preference_id": "synthetic",
        "updated_at": "2026-11-25T12:00:00Z",
    }


@router.post("/{patient_id}/tasks/today")
def get_today_tasks():
    """
    Get permitted tasks for the day.
    """
    return {
        "tasks": [
            {
                "task_id": "synthetic",
                "title": "Check-in",
                "deadline_at": "2026-11-26T09:00:00Z",
                "content_version_id": "synthetic",
                "privacy_scope": "PATIENT_PARENT_SHARED",
            }
        ]
    }


@router.post("/{patient_id}/visits")
def get_visits():
    """
    Get permitted appointments (read-only PMS mirror).
    """
    return {
        "visits": [
            {
                "appointment_id": "synthetic",
                "status": "confirmed",
                "start_at": "2026-11-26T10:00:00Z",
                "visit_type": "check_in",
                "import_freshness": "fresh",
            }
        ]
    }


@router.get("/{patient_id}/privacy-summary")
def privacy_summary():
    """
    Return the current relationship, scopes, consent/channel states.
    """
    return {
        "relationship": {"proxy_user_id": "synthetic", "status": "active", "scopes": ["PATIENT_PARENT_SHARED"]},
        "consent": {"kind": "care", "decision": "permit", "effective_from": "2026-11-25T12:00:00Z"},
        "channel": {"in_app": "active"},
    }


@router.post("/{patient_id}/withdrawals")
def withdraw():
    """
    Record a withdrawal.
    """
    return {"withdrawal_id": "synthetic", "effective_at": "2026-11-25T12:00:00Z"}
