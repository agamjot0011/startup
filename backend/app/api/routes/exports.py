from fastapi import APIRouter

router = APIRouter(prefix="/v1/exports", tags=["Exports"])


# ---------------------------------------------------------------------------
#  /v1/exports  -- approved record package
# ---------------------------------------------------------------------------


@router.get("")
def list_exports():
    """
    List approved record exports.
    """
    return {
        "exports": [
            {
                "export_id": "synthetic",
                "purpose": "records",
                "state": "ready",
                "created_at": "2026-11-25T12:00:00Z",
            }
        ]
    }
