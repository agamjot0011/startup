"""
WZDM LiveRecord - Backend entry point.

Run with:
    uvicorn server:app --reload
or:
    python -m uvicorn server:app --reload
"""

from app.core.config import settings
from app.main import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
