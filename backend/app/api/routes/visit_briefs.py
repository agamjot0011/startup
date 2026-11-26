from fastapi import APIRouter

router = APIRouter(prefix="/v1/staff", tags=["Staff Operations"])
canonical_router = APIRouter(prefix="/v1", tags=["Operations (alias)"])


# ---------------------------------------------------------------------------
#  /v1/staff/visit-briefs  -- chairside source capture and doctor sign-off
# ---------------------------------------------------------------------------


@router.get("/visit-briefs/{appointment_id}")
def get_visit_brief(appointment_id: str):
    """
    Get the visit brief for an appointment.
    """
    return {
        "appointment_id": appointment_id,
        "events_since_cutoff": [],
        "assistant_captures": [],
        "open_cards": [],
        "source_watermark": "synthetic",
        "projection_generated_at": "2026-11-25T12:00:00Z",
        "row_version": 1,
    }


@router.post("/visit-briefs/{brief_id}/output-selections")
def select_output(brief_id: str):
    """Record selected approved content versions (no generated prose)."""
    return {
        "brief_id": brief_id,
        "selected_outputs": ["synthetic content version"],
        "row_version": 2,
    }


# ---------------------------------------------------------------------------
#  /v1/operations  -- huddle, loop report, alert budget
# ---------------------------------------------------------------------------


@router.get("/operations/huddle")
def get_huddle():
    """
    Get the daily huddle projection.
    """
    return {
        "huddle_date": "2026-11-25",
        "open_cards": [],
        "overdue_cards": [],
        "closed_cards": [],
        "import_freshness": "fresh",
        "practice": "synthetic",
    }


@router.get("/operations/loop-report")
def get_loop_report():
    """
    Get the loop/card report.
    """
    return {
        "date": "2026-11-25",
        "open_loops": [],
        "overdue_loops": [],
        "closed_loops": [],
        "report_generated_at": "2026-11-25T12:00:00Z",
    }


@router.get("/operations/alert-budget")
def get_alert_budget():
    """
    Get alert budget and dismissal console.
    """
    return {
        "budget": {
            "orthodontist": {"limit": 2, "used_today": 0},
            "clinical_assistant": {"limit": 10, "used_today": 0},
        },
        "quiet_hours": {"active": False, "start": "22:00", "end": "07:00"},
        "dismissed": [],
    }


# Canonical handbook paths: /v1/operations/* (aliases of the staff-prefixed handlers)
canonical_router.add_api_route(
    "/operations/huddle", get_huddle, methods=["GET"],
    name="canonical_huddle",
)
canonical_router.add_api_route(
    "/operations/loop-report", get_loop_report, methods=["GET"],
    name="canonical_loop_report",
)
canonical_router.add_api_route(
    "/operations/alert-budget", get_alert_budget, methods=["GET"],
    name="canonical_alert_budget",
)
