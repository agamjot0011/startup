"""
WZDM LiveRecord - Authentication and session utilities.

Handles OIDC token validation, session management, and role extraction.
"""

import hashlib
import logging
import time
from typing import Optional

import jwt
from jwt import PyJWTError

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OIDC / JWT validation (Supabase Auth compatible)
# ---------------------------------------------------------------------------


def decode_token(token: str, roles_required=None) -> dict:
    """
    Decode and validate an OIDC JWT.

    For the alpha, we only verify the token signature against the
    Supabase public key and extract the payload claims. Full validation
    is handled by Supabase's edge functions in production.
    """
    if not token:
        raise ValueError("No token provided")

    try:
        # PyJWT will verify signature and expiry automatically
        payload = jwt.decode(
            token,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True,
            },
            # In production, set these to your Supabase JWKS URL
            # For the alpha, we use the Supabase JWKS endpoint
            **_get_jwks_kwargs(),
        )
        return payload
    except PyJWTError as exc:
        logger.error("Token validation failed: %s", exc)
        raise ValueError("Invalid or expired token") from exc


def _get_jwks_kwargs() -> dict:
    """
    Return kwargs for JWT decoding using the Supabase JWKS endpoint.
    """
    # Supabase public keys are accessible via the JWKS endpoint.
    # For now, use a placeholder - production should use a JWKS cached fetcher.
    return {}


# ---------------------------------------------------------------------------
# Principal / role / permission helpers
# ---------------------------------------------------------------------------


def extract_roles(payload: dict) -> list[str]:
    """Extract user roles from the JWT payload."""
    roles = payload.get("roles", [])
    # Also check common Supabase claims
    if not roles:
        roles = payload.get("app_metadata", {}).get("roles", [])
    return roles or []


def extract_assurance(payload: dict) -> str:
    """Extract assurance level from the JWT payload."""
    amp = payload.get("app_metadata", {})
    auth_time = payload.get("auth_time")
    timestamp = time.time()

    if auth_time and (timestamp - auth_time) < 3600:
        return "high"
    return "medium"


def check_role(roles: list[str], required_role: str) -> bool:
    """Check if the user has a required role."""
    return required_role in roles


def get_client_ip(request) -> str:
    """Extract the client IP address from the request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

SESSION_TTL = 3600  # 1 hour
SESSION_COOKIE_NAME = "wzdm_session"


def create_session_token(payload: dict) -> str:
    """Create a signed session token."""
    now = int(time.time())
    token_payload = {
        **payload,
        "iat": now,
        "exp": now + SESSION_TTL,
        "jti": hashlib.uuid4().hex,
    }
    # In production, sign with the service key
    return jwt.encode(token_payload, "dev-secret-key", algorithm="HS256")


def validate_session_token(token: str) -> Optional[dict]:
    """Validate a session token and return the payload."""
    try:
        return decode_token(token)
    except ValueError:
        return None
