from fastapi import APIRouter

router = APIRouter(prefix="/v1/family", tags=["Family"])


# ---------------------------------------------------------------------------
#  /v1/family/invitations  -- invited activation
#  /v1/family/recovery   -- practice-governed recovery
# ---------------------------------------------------------------------------


@router.get("/invitations")
def list_family_invitations():
    """
    List family invitations (single-use, hashed tokens).
    Scale: limited payload for the alpha.
    """
    return {
        "invitations": [
            {
                "invitation_id": "synthetic",
                "patient_id": "synthetic",
                "destination_ref": "synthetic@example.com",
                "status": "sent",
                "expires_at": "2026-11-26T12:00:00Z",
            }
        ]
    }


@router.post("/invitations")
def create_family_invitation():
    """
    Create a single-use, 15-minute family invitation.
    Returns invitation ID, expiry, and safe delivery status.
    """
    return {
        "invitation_id": "synthetic",
        "status": "sent",
        "expires_at": "2026-11-26T12:00:00Z",
        "max_attempts": 5,
    }


@router.post("/invitations/{invitation_id}/redeem")
def redeem_family_invitation(invitation_id: str):
    """
    Redeem a family invitation with an opaque token.
    Returns bound user/link and authenticator prompts.
    """
    return {
        "user_id": "synthetic",
        "patient_id": "synthetic",
        "authenticator_prompt": "passkey",
        "sharing_summary_reference": "synthetic",
    }


@router.post("/recovery/start")
def start_family_recovery():
    """
    Start a non-enumerating family recovery request.
    """
    return {"status": "accepted", "next_step": "practice-assisted-verification"}


@router.post("/recovery/{recovery_id}/complete")
def complete_family_recovery(recovery_id: str):
    """
    Complete recovery; old sessions/tokens revoked.
    """
    return {
        "status": "completed",
        "old_sessions_revoked": True,
        "new_authenticator": "synthetic",
    }
