from fastapi import APIRouter

router = APIRouter(prefix="/v1/proxy-relationships", tags=["Proxy Relationships"])


# ---------------------------------------------------------------------------
#  /v1/proxy-relationships  -- verified proxy authority
# ---------------------------------------------------------------------------


@router.get("")
def list_proxy_relationships():
    """
    List proxy relationships.
    """
    return {
        "relationships": [
            {
                "relationship_id": "synthetic",
                "patient_id": "synthetic",
                "status": "active",
                "authority_scopes": ["PATIENT_PARENT_SHARED"],
                "policy_version_id": "synthetic",
            }
        ]
    }


@router.post("")
def create_proxy_relationship():
    """
    Create a proxy relationship.
    """
    return {
        "relationship_id": "synthetic",
        "patient_id": "synthetic",
        "status": "active",
        "authority_scopes": ["PATIENT_PARENT_SHARED"],
    }


@router.post("/{relationship_id}/revocations")
def revoke_proxy_relationship(relationship_id: str):
    """
    Revoke a proxy relationship.
    """
    return {
        "relationship_id": relationship_id,
        "status": "revoked",
        "revoked_at": "2026-11-25T12:00:00Z",
    }
