# Authentication and session service

from app.db.session import SessionLocal
from app.schemas.sessions import PrincipalResponse


def get_principal() -> PrincipalResponse:
    """
    Get the current principal from the database.
    For the alpha, returns a synthetic principal because OIDC is not yet configured.
    """
    db = SessionLocal()
    try:
        return PrincipalResponse(
            actor_type="synthetic",
            assurance="unauthenticated",
            active_practice="synthetic",
            permitted_roles=["synthetic"],
            linked_patient_contexts=[],
            safe_prompts=["practice_phone", "emergency_text"],
        )
    finally:
        db.close()


def get_principal_id() -> str:
    """
    Get the current principal ID.
    """
    return "synthetic"
