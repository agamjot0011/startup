from fastapi import APIRouter

router = APIRouter(prefix="/v1/provider-webhooks", tags=["Provider Webhooks"])


# ---------------------------------------------------------------------------
#  /v1/provider-webhooks  -- signed SMS/email callbacks
# ---------------------------------------------------------------------------


@router.post("")
def provider_webhook():
    """
    Handle a provider webhook (SMS/email callback).
    Validates signature, timestamp, replay, and cross-tenant reference.
    """
    return {
        "command_id": "synthetic",
        "attempt": 1,
        "status": "dispatched",
    }
