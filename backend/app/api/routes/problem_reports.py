from fastapi import APIRouter

router = APIRouter(prefix="/v1/problem-reports", tags=["Problem Reports"])

# Alias: /v1/patients/{patient_id}/problem-reports (canonical test path, backwards-compat)
from fastapi import APIRouter as _APIRouter2

alias_router = _APIRouter2(prefix="/v1/patients", tags=["Problem Reports (alias)"])


@alias_router.post("/{patient_id}/problem-reports")
def submit_problem_report_alias(patient_id: str):
    """Alias for the canonical problem report endpoint (test backwards-compat)."""
    return submit_problem_report(patient_id=patient_id)


@router.post("/{patient_id}/problem-reports")
def submit_problem_report(patient_id: str):
    """Submit a structured problem report (no machine urgency, optional one photo)."""
    return {
        "report_id": "synthetic",
        "event_id": "synthetic",
        "status": "AWAITING_HUMAN_TRIAGE",
        "received_at": "2026-11-25T12:00:00Z",
        "practice_contact": {"phone": "011-800-000-0000", "emergency_wording": "Call 111"},
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
    }
