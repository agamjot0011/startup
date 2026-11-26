from fastapi import APIRouter

router = APIRouter(prefix="/v1/attachments", tags=["Attachments"])


# ---------------------------------------------------------------------------
#  /v1/attachments  -- constrained upload completion and short-lived reads
# ---------------------------------------------------------------------------


@router.post("/patient/{patient_id}/upload-slots")
def create_upload_slot(patient_id: str):
    """
    Create a constrained upload slot (max 15 MiB, JPEG/PNG only, SHA-256).
    """
    return {
        "attachment_id": "synthetic",
        "state": "UPLOAD_PENDING",
        "expires_at": "2026-11-25T12:05:00Z",
    }


@router.post("/patient/{patient_id}/upload-slots/{slot_id}/complete")
def complete_upload():
    """
    Confirm direct upload completion and checksum.
    """
    return {
        "attachment_id": "synthetic",
        "state": "QUARANTINED",
        "quarantine_checks": ["mime", "checksum", "size", "dimensions", "parser_safety"],
    }


@router.get("/{attachment_id}/access-link")
def get_access_link(attachment_id: str):
    """
    Get a fresh 60-second read link for an AVAILABLE attachment.
    """
    return {
        "attachment_id": attachment_id,
        "url": "synthetic-signed-url",
        "expires_at": "2026-11-25T12:01:00Z",
    }
