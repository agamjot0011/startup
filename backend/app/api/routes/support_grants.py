from fastapi import APIRouter

router = APIRouter(prefix="/v1/support-grants", tags=["Support Grants"])


# ---------------------------------------------------------------------------
#  /v1/support-grants  -- scoped, ticketed support access
# ---------------------------------------------------------------------------


@router.get("")
def list_support_grants():
    """
    List support grants.
    """
    return {
        "grants": [
            {
                "grant_id": "synthetic",
                "support_user_id": "synthetic",
                "purpose_code": "technical",
                "scope_json": {"feature": "read-only"},
                "status": "active",
            }
        ]
    }


@router.post("")
def create_support_grant():
    """
    Create a support grant.
    """
    return {
        "grant_id": "synthetic",
        "purpose_code": "technical",
        "scope_json": {"feature": "read-only"},
        "status": "active",
    }
