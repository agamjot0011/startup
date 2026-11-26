"""In-app messaging tests — views are never acknowledgements."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.event_ledger import event_ledger
from app.services.messaging_service import MessagingError, messaging_service
from app.services.session_service import session_store

client = TestClient(app)


def _session(role, user):
    return session_store.create(
        user_id=user, assurance="high", auth_methods=["oidc", "mfa"],
        practice_id="wzdm-01", membership_id=f"m-{user}", roles=[role],
    )


def _headers(s):
    return {"Authorization": f"Bearer {s.session_id}"}


def test_publish_writes_event_and_view_is_not_acknowledgement():
    author = _session("clinical_assistant", "msg-author")
    before = len(event_ledger._order)
    message = messaging_service.publish("wzdm-01", "p-1000", "Your summary is ready", author)
    assert event_ledger._events[event_ledger._order[-1]].event_type == "in_app_message_published.v1"

    patient = _session("patient", "msg-patient")
    view = messaging_service.view(message.message_id, patient)
    assert view["is_acknowledgement"] is False
    assert event_ledger._events[event_ledger._order[-1]].event_type == "message_viewed.v1"
    assert message.public()["view_is_not_acknowledgement"] is True
    assert len(event_ledger._order) == before + 2


def test_empty_body_rejected():
    author = _session("clinical_assistant", "msg-author2")
    try:
        messaging_service.publish("wzdm-01", "p-1001", "  ", author)
    except MessagingError as exc:
        assert exc.code == "MESSAGE_BODY_REQUIRED"
    else:
        raise AssertionError("expected empty body rejection")


def test_api_publish_read_and_view():
    assistant = _session("clinical_assistant", "msg-api-author")
    patient = _session("patient", "msg-api-patient")
    dentist = _session("orthodontist", "msg-api-dentist")

    published = client.post(
        "/v1/patients/p-1002/messages",
        json={"body": "Appointment confirmed"}, headers=_headers(assistant),
    )
    assert published.status_code == 200
    mid = published.json()["message_id"]

    listed = client.get("/v1/patients/p-1002/messages", headers=_headers(patient))
    assert listed.status_code == 200
    assert listed.json()["messages"][0]["message_id"] == mid

    viewed = client.post(f"/v1/messages/{mid}/views", headers=_headers(patient))
    assert viewed.status_code == 200
    assert viewed.json()["is_acknowledgement"] is False

    # A dentist without patient scope cannot read the patient's messages.
    denied = client.get("/v1/patients/p-1002/messages", headers=_headers(dentist))
    assert denied.status_code == 403
