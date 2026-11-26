"""
WZDM LiveRecord - Middleware.

Custom ASGI middleware for request/response processing, including
audit logging, idempotency, and request tracking.
"""

import hashlib
import logging
import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs audit entries for all requests.

    Records: actor, action, resource, patient_id, purpose, outcome.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        path = request.url.path
        method = request.method

        # Extract user context from headers (set by auth layer)
        actor_id = request.headers.get("X-User-ID", "system")
        actor_type = request.headers.get("X-User-Type", "system")

        # Extract patient context
        patient_id = request.headers.get("X-Patient-ID")

        # Process the request
        response = await call_next(request)

        # Build audit entry
        duration_ms = int((time.time() - start_time) * 1000)
        audit_payload = {
            "actor_user_id": actor_id,
            "actor_type": actor_type,
            "action": f"{method} {path}",
            "resource_type": self._infer_resource_type(path),
            "resource_id": self._extract_resource_id(path),
            "patient_id": patient_id,
            "duration_ms": duration_ms,
            "status_code": response.status_code,
        }

        # Only log significant requests
        if audit_payload["status_code"] >= 400 or method in ("POST", "PUT", "DELETE"):
            logger.info("Audit: %s", audit_payload)

        return response

    @staticmethod
    def _infer_resource_type(path: str) -> str:
        """Infer the resource type from the request path."""
        if "/patients" in path:
            return "patient"
        if "/cards" in path:
            return "card"
        if "/events" in path:
            return "care_event"
        if "/audit" in path:
            return "audit_entry"
        return "api"

    @staticmethod
    def _extract_resource_id(path: str) -> Optional[str]:
        """Extract a resource ID from the path."""
        parts = path.strip("/").split("/")
        # Resource IDs are UUIDs
        for part in parts:
            if len(part) == 36 and part.count("-") == 4:
                return part
        return None


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces idempotency for POST/PUT/DELETE requests.

    Uses the Idempotency-Key header to detect duplicate requests.
    """

    def __init__(self, app, idempotency_store=None):
        super().__init__(app)
        self.idempotency_store = idempotency_store or {}

    async def dispatch(self, request: Request, call_next):
        method = request.method
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            idempotency_key = request.headers.get("Idempotency-Key")

            if idempotency_key:
                # Check if we've seen this request before
                if idempotency_key in self.idempotency_store:
                    cached = self.idempotency_store[idempotency_key]
                    logger.info("Idempotent request rejected: %s", idempotency_key)
                    return Response(
                        content=cached,
                        status_code=200,
                        headers={"X-Idempotent-Replayed": "true"},
                    )

        response = await call_next(request)
        return response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds request timing and correlation headers.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)

        duration_ms = int((time.time() - start_time) * 1000)
        correlation_id = request.headers.get("X-Correlation-ID")

        response.headers["X-Response-Time"] = str(duration_ms)
        if correlation_id:
            response.headers["X-Correlation-ID"] = correlation_id

        return response
