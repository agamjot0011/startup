from fastapi import APIRouter

router = APIRouter(prefix="/v1/content-items", tags=["Content Governance"])


# ---------------------------------------------------------------------------
#  /v1/content-items  -- governed content library
# ---------------------------------------------------------------------------


@router.get("")
def list_content_items():
    """
    List content items.
    """
    return {
        "content_items": [
            {
                "content_item_id": "synthetic",
                "semantic_key": "synthetic",
                "class": "home_look_for",
                "audience": "patient",
                "purpose": "safety",
            }
        ]
    }


@router.get("/{content_item_id}/versions")
def list_content_versions():
    """
    List content versions for an item.
    """
    return {
        "content_versions": [
            {
                "content_version_id": "synthetic",
                "version_number": 1,
                "locale": "en",
                "state": "active",
                "checksum": "synthetic",
            }
        ]
    }


@router.post("/{content_item_id}/versions")
def create_content_version():
    """
    Create a content version draft.
    """
    return {
        "content_version_id": "synthetic",
        "version_number": 1,
        "state": "draft",
        "checksum": "synthetic",
    }


@router.post("/content-versions/{content_version_id}/approvals")
def approve_content_version():
    """
    Approve a content version.
    """
    return {
        "content_version_id": "synthetic",
        "state": "approved",
        "approved_at": "2026-11-25T12:00:00Z",
    }


@router.post("/content-versions/{content_version_id}/activations")
def activate_content_version():
    """
    Activate a content version.
    """
    return {
        "content_version_id": "synthetic",
        "state": "active",
        "activated_at": "2026-11-25T12:00:00Z",
    }


@router.post("/content-versions/{content_version_id}/safety-withdrawals")
def withdraw_content_version():
    """
    Withdraw a content version (safety).
    """
    return {
        "content_version_id": "synthetic",
        "state": "withdrawn",
        "withdrawn_at": "2026-11-25T12:00:00Z",
        "affected_work_reference": "synthetic",
    }


# Router for standalone endpoints without the /content-items prefix
# Used for test backwards-compat
content_version_alias_router = APIRouter(prefix="/v1/content-versions", tags=["Content Versions (alias)"])


@content_version_alias_router.post("/{content_version_id}/approvals")
def approve_content_version_alias(content_version_id: str):
    """Alias for the canonical content version approval endpoint (test backwards-compat)."""
    return approve_content_version()


@content_version_alias_router.post("/{content_version_id}/activations")
def activate_content_version_alias(content_version_id: str):
    """Alias for the canonical content version activation endpoint (test backwards-compat)."""
    return activate_content_version()


@content_version_alias_router.post("/{content_version_id}/safety-withdrawals")
def withdraw_content_version_alias(content_version_id: str):
    """Alias for the canonical content version withdrawal endpoint (test backwards-compat)."""
    return withdraw_content_version()
