# Rule service

from app.db.session import SessionLocal


def list_rule_versions():
    """
    List rule versions.
    """
    return [
        {
            "rule_version_id": "synthetic",
            "version_number": 1,
            "state": "active",
            "checksum": "synthetic",
        }
    ]
