"""Notification pipeline tests — fail-closed PHI scanner, gates and budgets."""

from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.services.event_ledger import event_ledger
from app.services.notification_service import (
    ALLOWED_TEMPLATES,
    NotificationError,
    notification_service,
    scan_for_phi,
)
from app.services.session_service import session_store

client = TestClient(app)


def _manager():
    return session_store.create(
        user_id="notification-manager", assurance="high", auth_methods=["oidc", "mfa"],
        practice_id="wzdm-01", membership_id="m-manager", roles=["practice_manager"],
    )


def _headers(s):
    return {"Authorization": f"Bearer {s.session_id}"}


def test_fail_closed_phi_scanner():
    assert scan_for_phi("Your summary is in the app.").passed is True
    for content in [
        "Email me at joy@example.com",
        "Call 555-010-2200",
        "Patient p-1234 record",
        "Visit on 2026-11-26",
        "Diagnosis: caries noted",
    ]:
        result = scan_for_phi(content)
        assert result.passed is False, content
        assert result.findings


def test_phi_template_is_blocked_and_audited():
    ALLOWED_TEMPLATES["unsafe_test"] = "Contact joy@example.com about p-1234"
    try:
        before = len(event_ledger._order)
        command = notification_service.enqueue(
            practice_id="wzdm-01", site_id="site-1", patient_id="p-800",
            template_id="unsafe_test", channel="sms", role="clinical_assistant",
        )
        assert command.status == "BLOCKED"
        assert command.blocked_reason and "PHI_SCAN_FAILED" in command.blocked_reason
        new_events = event_ledger._order[before:]
        assert event_ledger._events[new_events[0]].event_type == "notification_blocked.v1"
        assert event_ledger._events[new_events[1]].event_type == "notification_commanded.v1"
        assert len(new_events) == 2
    finally:
        del ALLOWED_TEMPLATES["unsafe_test"]


def test_provider_gate_fallback():
    notification_service.configure_provider("site-2", sms=False, email=False)
    command = notification_service.enqueue(
        practice_id="wzdm-01", site_id="site-2", patient_id="p-801",
        template_id="digest_weekly", channel="sms", role="clinical_assistant",
    )
    assert command.status == "FALLBACK_IN_APP"
    assert command.provider is None


def test_quiet_hours_defers_and_urgent_bypasses():
    night = datetime(2026, 11, 26, 23, 30, tzinfo=timezone.utc)
    routine = notification_service.enqueue(
        practice_id="wzdm-01", site_id="site-3", patient_id="p-802",
        template_id="digest_weekly", channel="in_app", role="clinical_assistant", now=night,
    )
    assert "T07:00:00" in routine.not_before
    urgent = notification_service.enqueue(
        practice_id="wzdm-01", site_id="site-3", patient_id="p-802",
        template_id="urgent_notice", channel="in_app", role="orthodontist",
        urgent=True, now=night,
    )
    assert datetime.fromisoformat(urgent.not_before) == night


def test_budget_enforcement_and_dispatch():
    notification_service.configure_provider("site-4", sms=True, email=True)
    morning = datetime(2026, 11, 27, 9, 0, tzinfo=timezone.utc)
    first = notification_service.enqueue(
        practice_id="wzdm-01", site_id="site-4", patient_id="p-803",
        template_id="appointment_reminder", channel="sms", role="orthodontist", now=morning,
    )
    second = notification_service.enqueue(
        practice_id="wzdm-01", site_id="site-4", patient_id="p-804",
        template_id="appointment_reminder", channel="sms", role="orthodontist", now=morning,
    )
    assert first.status == "PENDING"
    assert second.status == "PENDING"

    result = notification_service.dispatch_pending(now=morning)
    assert result["dispatched"] >= 2

    third = notification_service.enqueue(
        practice_id="wzdm-01", site_id="site-4", patient_id="p-805",
        template_id="appointment_reminder", channel="sms", role="orthodontist", now=morning,
    )
    assert third.status == "BUDGET_EXCEEDED"


def test_unapproved_template_rejected():
    try:
        notification_service.enqueue(
            practice_id="wzdm-01", site_id="site-5", patient_id="p-806",
            template_id="free_text", channel="email", role="clinical_assistant",
        )
    except NotificationError as exc:
        assert exc.code == "UNAPPROVED_TEMPLATE"
    else:
        raise AssertionError("expected unapproved template rejection")


def test_api_health_requires_manager_and_step_up():
    manager = _manager()
    ok = client.get("/v1/notifications/health", headers=_headers(manager))
    assert ok.status_code == 200
    assert "status_counts" in ok.json()

    assistant = session_store.create(
        user_id="notif-assistant", assurance="high", auth_methods=["oidc"],
        practice_id="wzdm-01", membership_id="m-a", roles=["clinical_assistant"],
    )
    denied = client.get("/v1/notifications/health", headers=_headers(assistant))
    assert denied.status_code == 403
