"""Card state machine tests — explicit acknowledgement and forbidden transitions."""

import pytest

from app.services.card_state import (
    ACKNOWLEDGED,
    CLOSED,
    OPEN,
    RESULT_RECORDED,
    STARTED,
    CardStateError,
    card_service,
)
from app.services.event_ledger import event_ledger


def _card(patient="p-300"):
    return card_service.create(
        practice_id="wzdm-01", patient_id=patient, card_type="bond_check",
        owner_membership_id="membership-1", owner_role="clinical_assistant",
        deadline="2026-11-27T09:00:00Z",
    )


def test_delivery_is_not_acknowledgement():
    card = _card()
    assert card.state == OPEN
    assert card_service.get(card.card_id).state == OPEN


def test_happy_path_with_version_increments():
    card = _card("p-301")
    cid = card.card_id
    assert card_service.acknowledge(cid, expected_version=1).state == ACKNOWLEDGED
    assert card_service.start(cid, expected_version=2).state == STARTED
    assert card_service.result(cid, "completed", expected_version=3).state == RESULT_RECORDED
    done = card_service.close(cid, expected_version=4)
    assert done.state == CLOSED
    assert done.row_version == 5
    assert done.result_code == "completed"


@pytest.mark.parametrize("action,kwargs,expected", [
    ("start", {}, "FORBIDDEN_TRANSITION"),
    ("result", {"result_code": "done"}, "FORBIDDEN_TRANSITION"),
    ("close", {}, "FORBIDDEN_TRANSITION"),
])
def test_forbidden_transitions_from_open(action, kwargs, expected):
    card = _card()
    with pytest.raises(CardStateError) as exc:
        getattr(card_service, action)(card.card_id, **kwargs)
    assert exc.value.code == expected
    assert card_service.get(card.card_id).state == OPEN


def test_stale_version_rejected():
    card = _card()
    with pytest.raises(CardStateError) as exc:
        card_service.acknowledge(card.card_id, expected_version=99)
    assert exc.value.code == "STALE_ROW_VERSION"
    assert card_service.get(card.card_id).row_version == 1


def test_terminal_states_reject_further_transitions():
    card = _card()
    card_service.acknowledge(card.card_id)
    card_service.start(card.card_id)
    card_service.result(card.card_id, "done")
    card_service.close(card.card_id)
    with pytest.raises(CardStateError) as exc:
        card_service.acknowledge(card.card_id)
    assert exc.value.code == "FORBIDDEN_TRANSITION"


def test_cancellation_requires_reason():
    card = _card()
    with pytest.raises(CardStateError) as exc:
        card_service.cancel(card.card_id, "")
    assert exc.value.code == "CANCELLATION_REASON_REQUIRED"
    cancelled = card_service.cancel(card.card_id, "patient withdrawn")
    assert cancelled.cancellation_reason == "patient withdrawn"


def test_reassign_and_reschedule_are_versioned():
    card = _card()
    reassigned = card_service.reassign(card.card_id, "membership-2", "orthodontist")
    assert reassigned.row_version == 2
    assert reassigned.owner_role == "orthodontist"
    rescheduled = card_service.reschedule(card.card_id, "2026-11-28T09:00:00Z")
    assert rescheduled.row_version == 3
    assert rescheduled.deadline == "2026-11-28T09:00:00Z"


def test_every_transition_appends_a_ledger_event():
    card = _card("p-302")
    count_before = len(event_ledger._order)
    card_service.acknowledge(card.card_id)
    card_service.start(card.card_id)
    card_service.result(card.card_id, "done")
    card_service.close(card.card_id)
    order = event_ledger._order[count_before:]
    types = [event_ledger._order and event_ledger._events[e].event_type for e in order]
    assert "card_acknowledged.v1" in types
    assert "card_started.v1" in types
    assert "card_result_recorded.v1" in types
    assert "card_closed.v1" in types
    assert event_ledger.verify() is True
