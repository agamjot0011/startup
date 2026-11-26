from fastapi import APIRouter

router = APIRouter(prefix="/v1/audit", tags=["Audit"])


# ---------------------------------------------------------------------------
#  /v1/audit  -- restricted access/disclosure report
# ---------------------------------------------------------------------------


@router.get("")
def list_audit_entries():
    """
    List audit entries (restricted to designated roles).
    """
    return {
        "audit_entries": [
            {
                "audit_id": "synthetic",
                "action": "log_in",
                "resource_type": "user",
                "resource_id": "synthetic",
                "created_at": "2026-11-25T12:00:00Z",
            }
        ]
    }
