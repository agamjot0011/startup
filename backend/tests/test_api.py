import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "WZDM LiveRecord API"


def test_live_health_endpoint():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.skip(reason="Database not configured in test environment - requires Supabase credentials")
def test_ready_health():
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["database"] == "connected"


def _auth_headers():
    sign_in = client.post(
        "/v1/sessions", json={"session": "smoke-user", "password": "smoke-password"}
    )
    assert sign_in.status_code == 200
    return {"Authorization": f"Bearer {sign_in.json()['session_id']}"}


def test_v1_me_endpoint():
    response = client.get("/v1/me", headers=_auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert "user_id" in body
    assert "safe_prompts" in body


def test_v1_session_context():
    response = client.post(
        "/v1/sessions/practice-context",
        json={"practice_id": "wzdm-01", "expected_session_version": 1},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["active"] is True


def test_v1_session_revoke():
    response = client.delete("/v1/sessions/current", headers=_auth_headers())
    assert response.status_code == 204


def test_v1_family_invitations():
    response = client.get("/v1/family/invitations")
    assert response.status_code == 200


def test_v1_create_family_invitation():
    response = client.post("/v1/family/invitations")
    assert response.status_code == 200
    body = response.json()
    assert "invitation_id" in body
    assert body["status"] == "sent"


def test_v1_redeem_family_invitation():
    response = client.post("/v1/family/invitations/synthetic/redeem")
    assert response.status_code == 200
    body = response.json()
    assert "user_id" in body


def test_v1_start_family_recovery():
    response = client.post("/v1/family/recovery/start")
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_v1_complete_family_recovery():
    response = client.post("/v1/family/recovery/synthetic/complete")
    assert response.status_code == 200


def test_v1_list_patients():
    response = client.get("/v1/patients")
    assert response.status_code == 200
    body = response.json()
    assert "patients" in body


def test_v1_create_patient():
    response = client.post("/v1/patients")
    assert response.status_code == 200
    body = response.json()
    assert "patient_id" in body


def test_v1_patient_family_home():
    response = client.get("/v1/patients/synthetic/family-home")
    assert response.status_code == 200
    body = response.json()
    assert "safe_route" in body


def test_v1_patient_timeline():
    response = client.get("/v1/patients/synthetic/timeline")
    assert response.status_code == 200
    body = response.json()
    assert "events" in body


def test_v1_patient_enrolment():
    response = client.post("/v1/patients/synthetic/enrolments")
    assert response.status_code == 200


def test_v1_identity_verification():
    response = client.post("/v1/patients/synthetic/identity-verifications")
    assert response.status_code == 200


def test_v1_proxy_relationship():
    response = client.post("/v1/proxy-relationships")
    assert response.status_code == 200
    body = response.json()
    assert "relationship_id" in body


def test_v1_list_proxy_relationships():
    response = client.get("/v1/proxy-relationships")
    assert response.status_code == 200


def test_v1_consent():
    response = client.post("/v1/consents")
    assert response.status_code == 200
    body = response.json()
    assert "consent_id" in body


def test_v1_list_consents():
    response = client.get("/v1/consents")
    assert response.status_code == 200


def test_v1_notification_preferences():
    response = client.get("/v1/patients/synthetic/notification-preferences")
    assert response.status_code == 200


def test_v1_update_notification_preferences():
    response = client.post("/v1/patients/synthetic/notification-preferences")
    assert response.status_code == 200


def test_v1_today_tasks():
    response = client.post("/v1/patients/synthetic/tasks/today")
    assert response.status_code == 200
    assert "tasks" in response.json()


def test_v1_problem_report():
    response = client.post("/v1/patients/synthetic/problem-reports")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "AWAITING_HUMAN_TRIAGE"


def test_v1_get_report():
    response = client.get("/v1/patients/synthetic/reports/synthetic")
    assert response.status_code == 200


def test_v1_attachments():
    response = client.post("/v1/attachments/patient/synthetic/upload-slots")
    assert response.status_code == 200
    body = response.json()
    assert "attachment_id" in body


def test_v1_upload_complete():
    response = client.post("/v1/attachments/patient/synthetic/upload-slots/synthetic/complete")
    assert response.status_code == 200


def test_v1_access_link():
    response = client.get("/v1/attachments/synthetic/access-link")
    assert response.status_code == 200


def test_v1_cards():
    response = client.get("/v1/cards")
    assert response.status_code == 200
    body = response.json()
    assert "cards" in body


def test_v1_card_detail():
    response = client.get("/v1/cards/synthetic")
    assert response.status_code == 200


def test_v1_card_acknowledge():
    response = client.post("/v1/cards/synthetic/acknowledgements")
    assert response.status_code == 200


def test_v1_card_start():
    response = client.post("/v1/cards/synthetic/starts")
    assert response.status_code == 200


def test_v1_card_result():
    response = client.post("/v1/cards/synthetic/results")
    assert response.status_code == 200


def test_v1_card_reassign():
    response = client.post("/v1/cards/synthetic/reassignments")
    assert response.status_code == 200


def test_v1_card_reschedule():
    response = client.post("/v1/cards/synthetic/reschedules")
    assert response.status_code == 200


def test_v1_card_cancel():
    response = client.post("/v1/cards/synthetic/cancellations")
    assert response.status_code == 200


def test_v1_visit_brief():
    response = client.get("/v1/staff/visit-briefs/synthetic")
    assert response.status_code == 200


def test_v1_select_output():
    response = client.post("/v1/staff/visit-briefs/synthetic/output-selections")
    assert response.status_code == 200


def test_v1_huddle():
    response = client.get("/v1/staff/operations/huddle")
    assert response.status_code == 200


def test_v1_loop_report():
    response = client.get("/v1/staff/operations/loop-report")
    assert response.status_code == 200


def test_v1_alert_budget():
    response = client.get("/v1/staff/operations/alert-budget")
    assert response.status_code == 200


def test_v1_import_register():
    response = client.post("/v1/imports/pms")
    assert response.status_code == 200
    body = response.json()
    assert "import_id" in body


def test_v1_import_status():
    response = client.get("/v1/imports/pms/synthetic")
    assert response.status_code == 200


def test_v1_import_commit():
    response = client.post("/v1/imports/pms/synthetic/commit")
    assert response.status_code == 200


def test_v1_list_rule_sets():
    response = client.get("/v1/rule-sets")
    assert response.status_code == 200


def test_v1_list_rule_versions():
    response = client.get("/v1/rule-sets/synthetic/versions")
    assert response.status_code == 200


def test_v1_create_rule_version():
    response = client.post("/v1/rule-sets/synthetic/versions")
    assert response.status_code == 200


def test_v1_submit_rule_version():
    response = client.post("/v1/rule-versions/synthetic/submissions")
    assert response.status_code == 200


def test_v1_approve_rule_version():
    response = client.post("/v1/rule-versions/synthetic/approvals")
    assert response.status_code == 200


def test_v1_activate_rule_version():
    response = client.post("/v1/rule-versions/synthetic/activations")
    assert response.status_code == 200


def test_v1_list_content_items():
    response = client.get("/v1/content-items")
    assert response.status_code == 200


def test_v1_list_content_versions():
    response = client.get("/v1/content-items/synthetic/versions")
    assert response.status_code == 200


def test_v1_create_content_version():
    response = client.post("/v1/content-items/synthetic/versions")
    assert response.status_code == 200


def test_v1_approve_content_version():
    response = client.post("/v1/content-versions/synthetic/approvals")
    assert response.status_code == 200


def test_v1_activate_content_version():
    response = client.post("/v1/content-versions/synthetic/activations")
    assert response.status_code == 200


def test_v1_withdraw_content_version():
    response = client.post("/v1/content-versions/synthetic/safety-withdrawals")
    assert response.status_code == 200


def test_v1_list_support_grants():
    response = client.get("/v1/support-grants")
    assert response.status_code == 200


def test_v1_create_support_grant():
    response = client.post("/v1/support-grants")
    assert response.status_code == 200


def test_v1_list_audit():
    response = client.get("/v1/audit")
    assert response.status_code == 200


def test_v1_list_exports():
    response = client.get("/v1/exports")
    assert response.status_code == 200


def test_v1_provider_webhook():
    response = client.post("/v1/provider-webhooks")
    assert response.status_code == 200
