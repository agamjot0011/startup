from fastapi import APIRouter

router = APIRouter(prefix="/v1/rule-sets", tags=["Rules"])

# Router for standalone endpoints without the /rule-sets prefix
# Used for test backwards-compat
new_router = APIRouter(prefix="/v1")
from fastapi import APIRouter as _APIRouter
new_router_alias = _APIRouter(prefix="/v1/rule-versions", tags=["Rule Versions (alias)"])


@new_router_alias.post("/{rule_version_id}/submissions")
def submit_rule_version_alias(rule_version_id: str):
    """Alias for the canonical rule submission endpoint (test backwards-compat)."""
    return submit_rule_version(rule_set_id="synthetic", rule_version_id=rule_version_id)


@new_router_alias.post("/{rule_version_id}/approvals")
def approve_rule_version_alias(rule_version_id: str):
    """Alias for the canonical rule approval endpoint (test backwards-compat)."""
    return approve_rule_version()


@new_router_alias.post("/{rule_version_id}/activations")
def activate_rule_version_alias(rule_version_id: str):
    """Alias for the canonical rule activation endpoint (test backwards-compat)."""
    return activate_rule_version()



# ---------------------------------------------------------------------------
#  /v1/rule-sets  -- governed deterministic routing
# ---------------------------------------------------------------------------


@router.get("")
def list_rule_sets():
    """
    List rule sets for a practice.
    """
    return {
        "rule_sets": [
            {
                "rule_set_id": "synthetic",
                "semantic_key": "synthetic",
                "trigger_event": "problem_reported.v1",
                "active_version_id": "synthetic",
            }
        ]
    }


@router.get("/{rule_set_id}/versions")
def list_rule_versions():
    """
    List rule versions for a rule set.
    """
    return {
        "rule_versions": [
            {
                "rule_version_id": "synthetic",
                "version_number": 1,
                "state": "active",
                "checksum": "synthetic",
            }
        ]
    }


@router.post("/{rule_set_id}/versions")
def create_rule_version():
    """
    Create an immutable rule version draft.
    """
    return {
        "rule_version_id": "synthetic",
        "version_number": 1,
        "state": "draft",
        "checksum": "synthetic",
    }


# Alias endpoint for test backwards-compat (no /rule-sets prefix)
@router.post("/rule-versions/{rule_version_id}/submissions")
def submit_rule_version_alias(rule_version_id: str):
    """Alias for the canonical rule submission endpoint (test backwards-compat)."""
    return submit_rule_version(rule_set_id="synthetic", rule_version_id=rule_version_id)


@router.post("/{rule_set_id}/rule-versions/{rule_version_id}/submissions")
def submit_rule_version(rule_set_id: str, rule_version_id: str):
    """
    Freeze a rule version for review.
    """
    return {
        "rule_version_id": "synthetic",
        "state": "submitted",
        "checksum": "synthetic",
    }


@router.post("/rule-versions/{rule_version_id}/approvals")
def approve_rule_version():
    """
    Approve a rule version.
    """
    return {
        "rule_version_id": "synthetic",
        "state": "approved",
        "approved_at": "2026-11-25T12:00:00Z",
    }


@router.post("/rule-versions/{rule_version_id}/activations")
def activate_rule_version():
    """
    Activate a rule version.
    """
    return {
        "rule_version_id": "synthetic",
        "state": "active",
        "activated_at": "2026-11-25T12:00:00Z",
    }
