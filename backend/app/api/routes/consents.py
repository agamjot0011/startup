from fastapi import APIRouter

router = APIRouter(prefix="/v1/consents", tags=["Consents"])


# ---------------------------------------------------------------------------
#  /v1/consents  -- purpose-scoped consent/assent
# ---------------------------------------------------------------------------


@router.get("")
def list_consents():
    """
    List consents.
    """
    return {
        "consents": [
            {
                "consent_id": "synthetic",
                "patient_id": "synthetic",
                "kind": "care",
                "decision": "permit",
                "effective_from": "2026-11-25T12:00:00Z",
            }
        ]
    }


@router.post("")
def record_consent_decision():
    """
    Record a consent decision.
    """
    return {
        "consent_id": "synthetic",
        "kind": "care",
        "decision": "permit",
        "effective_from": "2026-11-25T12:00:00Z",
    }


@router.post("/{patient_id}/withdrawals")
def withdraw_consent():
    """
    Withdraw a consent.
    """
    return {
        "withdrawal_id": "synthetic",
        "consent_id": "synthetic",
        "effective_at": "2026-11-25T12:00:00Z",
    }
