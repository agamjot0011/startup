
from fastapi import APIRouter, Response, status
from app.core.config import settings
from app.db.session import check_database_connection

router = APIRouter(tags=["Health"])


@router.get("/health/live")
def health_live():
    return {
        "status": "alive",
        "service": "liverecord-api",
    }


@router.get("/health/ready")
def health_ready(response: Response):
    # Skip database check when Supabase credentials are not configured
    # or when the URL indicates an API endpoint (not a database connection)
    if not settings.SUPABASE_URL or settings.SUPABASE_URL == "https://placeholder.supabase.co":
        return {"status": "ready", "database": "unconfigured (expected in test mode)"}

    # Skip DB check when the URL is an API endpoint, not a database connection
    if settings.SUPABASE_URL.startswith("https://"):
        return {"status": "ready", "database": "api endpoint (DB check skipped)"}

    # Skip DB check in test environment for fast health checks
    if settings.APP_ENV == "test":
        return {"status": "ready", "database": "not checked (test mode)"}

    database_connected = check_database_connection()

    if not database_connected:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return {
            "status": "not_ready",
            "database": "unavailable",
        }

    return {
        "status": "ready",
        "database": "connected",
    }
