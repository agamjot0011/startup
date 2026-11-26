from fastapi import APIRouter

router = APIRouter(prefix="/v1/cards", tags=["Cards"])


# ---------------------------------------------------------------------------
#  /v1/cards  -- role inboxes, card lifecycle, loops
# ---------------------------------------------------------------------------


@router.get("")
def list_cards():
    """
    Get the role-filtered card inbox.
    """
    return {
        "cards": [
            {
                "card_id": "synthetic",
                "card_type": "care_loop",
                "status": "available",
                "owner": "synthetic",
                "deadline_at": "2026-11-26T09:00:00Z",
                "loop_id": "synthetic",
            }
        ],
        "next_cursor": None,
    }


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
