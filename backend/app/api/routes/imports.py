from fastapi import APIRouter

router = APIRouter(prefix="/v1/imports", tags=["PMS Imports"])


# ---------------------------------------------------------------------------
#  /v1/imports/pms  -- quarantine, dry-run, commit, reconciliation
# ---------------------------------------------------------------------------


@router.post("/pms")
def register_pms_import():
    """
    Register an import from a quarantined ZIP package.
    """
    return {
        "import_id": "synthetic",
        "manifest_identity": "synthetic",
        "state": "validation",
        "row_version": 1,
    }


@router.get("/pms/{import_id}")
def get_import_status(import_id: str):
    """
    Get import status and reconciliation details.
    """
    return {
        "import_id": import_id,
        "state": "ready",
        "source": "synthetic",
        "batch_id": "synthetic",
        "row_counts": {"patients": 10, "appointments": 5},
        "pending_reconsiliation": [],
    }


@router.post("/pms/{import_id}/commit")
def commit_import(import_id: str):
    """Atomic commit of a reviewed import batch."""
    return {
        "import_id": import_id,
        "state": "committed",
        "committed_at": "2026-11-25T12:00:00Z",
        "counts": {"created": 10, "updated": 0, "unchanged": 5},
    }
