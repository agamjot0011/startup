"""
WZDM LiveRecord - Authentication & authorization routes.

Implements the OIDC/ROPC sign-in flow for the alpha with synthetic
credentials. In production, these are replaced by Supabase edge functions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.auth_service import get_principal

router = APIRouter(prefix="/auth", tags=["Auth"])


# ---------------------------------------------------------------------------
# /auth/signup -- alpha only (demo creation)
# ---------------------------------------------------------------------------


@router.post("/signup")
def signup(email: str = None, password: str = None, create_member: bool = False):
    """
    Create a new user and practice membership (alpha only).

    In production, this is handled by Supabase Auth + an edge function.
    """
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required",
        )

    # For the alpha, accept any credentials
    if create_member:
        return {
            "user_id": "synthetic",
            "member_id": "synthetic",
            "status": "approved",
            "role": "practice_member",
        }

    return {
        "user_id": "synthetic",
        "access_token": "synthetic-access-token",
        "token_type": "bearer",
        "expires_in": 3600,
        "assurance": "unauthenticated",
    }


# ---------------------------------------------------------------------------
# /auth/oidc -- OIDC token endpoint (alpha)
# ---------------------------------------------------------------------------


@router.post("/oidc/token")
def oidc_token_endpoint():
    """
    OIDC token endpoint (alpha stub).

    For the alpha, accepts any credentials and returns a synthetic token.
    Production: Supabase edge function.
    """
    return {
        "access_token": "synthetic-access-token",
        "token_type": "bearer",
        "expires_in": 3600,
        "scope": "openid profile email",
    }


# ---------------------------------------------------------------------------
# /auth/session
# ---------------------------------------------------------------------------


@router.get("/session")
def session_status(db: Session = Depends(get_db)):
    """Return the current session status."""
    principal = get_principal()
    return {"principal": principal}


# ---------------------------------------------------------------------------
# /auth/logout
# ---------------------------------------------------------------------------


@router.post("/logout")
def logout():
    """Revoke the current session."""
    return {"status": "revoked"}
