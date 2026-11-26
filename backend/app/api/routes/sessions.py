from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["Sessions"])


class SessionCreateRequest(BaseModel):
    session: str
    password: str


# ---------------------------------------------------------------------------
#  /v1/sessions  -- sign in (alpha)
# ---------------------------------------------------------------------------


@router.post("/v1/sessions")
def create_session(payload: SessionCreateRequest):
    """
    Alpha sign-in. Accepts any non-empty session identifier and password and
    returns a synthetic session. Production replaces this with Supabase Auth.
    """
    if not payload.session.strip() or not payload.password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session identifier and password are required",
        )
    return {
        "session_id": "synthetic",
        "access_token": "synthetic-access-token",
        "token_type": "bearer",
        "expires_in": 3600,
        "actor_type": "synthetic",
        "assurance": "unauthenticated",
        "active_practice": "synthetic",
        "permitted_roles": ["practice_member"],
    }


# ---------------------------------------------------------------------------
#  /v1/sessions  -- practice context, current identity/session, logout
# ---------------------------------------------------------------------------


@router.get("/v1/me")
def current_principal(db: Session = Depends(get_db)):
    """
    Return only the current identity, assurance, active practice,
    permitted roles, linked patient contexts and safe prompts.
    """
    # Supabase anon-key is identity-only; no sensitive data is returned.
    return {
        "actor_type": "unknown",
        "assurance": "unauthenticated",
        "active_practice": None,
        "permitted_roles": [],
        "linked_patient_contexts": [],
        "safe_prompts": ["practice_phone", "emergency_text"],
    }


@router.post("/v1/sessions/practice-context")
def select_practice_context():
    """
    Select an active practice from the actor's current memberships.
    For the alpha, returns a synthetic success because OIDC is not yet configured.
    """
    return {
        "practice_id": "synthetic",
        "membership_id": "synthetic",
        "active": True,
        "session_version": 1,
    }


@router.delete("/v1/sessions/current")
def revoke_current_session():
    """
    Idempotently revoke the current session.
    Returns 204 for the alpha (no real session store).
    """
    return Response(status_code=status.HTTP_204_NO_CONTENT)
