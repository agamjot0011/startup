"""Legacy session routes.

The session lifecycle now lives in ``app.api.routes.auth`` (handbook Step 5).
This module is retained as an import-compatible placeholder so no external
importer breaks; it intentionally registers no routes.
"""

from fastapi import APIRouter

router = APIRouter(tags=["Sessions"])
