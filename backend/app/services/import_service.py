# Import service

from app.db.session import SessionLocal


def get_import_status(import_id: str):
    """
    Get import status.
    """
    return {
        "import_id": import_id,
        "state": "ready",
        "row_counts": {"patients": 10, "appointments": 5},
    }
