from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.api.routes.auth import current_session
from app.services.card_state import card_service
from app.services.session_service import SessionRecord

router = APIRouter(prefix="/v1/cards", tags=["Cards"])


# ---------------------------------------------------------------------------
#  /v1/cards  -- role inboxes, card lifecycle, loops
# ---------------------------------------------------------------------------


@router.get("")
def list_cards(session: SessionRecord = Depends(current_session)):
    """Role-filtered card inbox, backed by the persisted card state."""
    def due_label(deadline: str) -> str:
        try:
            day = datetime.fromisoformat(deadline.replace("Z", "+00:00")).date()
            days = (day - datetime.now(timezone.utc).date()).days
            if days <= 0:
                return "Today"
            if days == 1:
                return "Tomorrow"
            return f"In {days} days"
        except (ValueError, TypeError):
            return "Today"

    state_map = {
        "OPEN": "open", "ACKNOWLEDGED": "acknowledged",
        "STARTED": "active", "RESULT_RECORDED": "active",
        "CLOSED": "done", "CANCELLED": "done",
    }
    cards = []
    for card in card_service.list_for_practice(session.active_practice_id):
        due = due_label(card.deadline)
        cards.append({
            "id": card.card_id, "card_id": card.card_id,
            "title": card.card_type.replace("_", " ").title(),
            "patient": card.patient_id,
            "role": card.owner_role.replace("_", " ").title() if card.owner_role else "Unassigned",
            "due": due,
            "state": state_map.get(card.state, "open"),
            "tone": "due" if due == "Today" else "neutral",
            "card_type": card.card_type, "deadline": card.deadline,
            "owner_membership_id": card.owner_membership_id,
            "owner_role": card.owner_role, "row_version": card.row_version,
            "result_code": card.result_code,
        })
    return cards


@router.get("/{card_id}")
def get_card(card_id: str):
    """
    Get the full ten-part card projection.
    """
    return {
        "card_id": card_id,
        "what_happened": "Synthetic source fact",
        "meaning_for_role": "Synthetic role context",
        "look_for": ["synthetic item 1", "synthetic item 2"],
        "action": "Do the approved action",
        "by_when": "2026-11-26 09:00 Local",
        "owner": "synthetic",
        "deadline_at": "2026-11-26T09:00:00Z",
        "status": "available",
        "row_version": 1,
    }


@router.post("/{card_id}/acknowledgements")
def acknowledge_card():
    """
    Explicit acknowledgement.
    """
    return {
        "acknowledgement_id": "synthetic",
        "card_id": "synthetic",
        "acknowledged_at": "2026-11-25T12:00:00Z",
        "actor": "synthetic",
    }


@router.post("/{card_id}/starts")
def start_card():
    """
    Start or claim a card.
    """
    return {
        "card_id": "synthetic",
        "status": "in_progress",
        "owner": "synthetic",
        "row_version": 2,
    }


@router.post("/{card_id}/results")
def record_result():
    """
    Record a typed result.
    """
    return {
        "result_id": "synthetic",
        "card_id": "synthetic",
        "result_code": "completed",
        "recorded_at": "2026-11-25T12:00:00Z",
        "card_row_version": 3,
    }


@router.post("/{card_id}/reassignments")
def reassign_card():
    """
    Reassign card ownership.
    """
    return {
        "card_id": "synthetic",
        "new_owner": "synthetic",
        "old_owner": "synthetic",
        "row_version": 4,
    }


@router.post("/{card_id}/reschedules")
def reschedule_card():
    """
    Reschedule card deadline.
    """
    return {
        "card_id": "synthetic",
        "new_deadline_at": "2026-11-27T09:00:00Z",
        "old_deadline_at": "2026-11-26T09:00:00Z",
        "row_version": 5,
    }


@router.post("/{card_id}/cancellations")
def cancel_card():
    """
    Cancel a card.
    """
    return {
        "card_id": "synthetic",
        "status": "cancelled",
        "cancelled_at": "2026-11-25T12:00:00Z",
        "row_version": 6,
    }
