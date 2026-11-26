
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="WZDM LiveRecord API - FastAPI + Supabase backend",
    version="0.1.0",
    debug=settings.DEBUG,
)

# Development-only CORS configuration.
# Production must use explicitly approved origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include the API router with all routes
app.include_router(api_router)


@app.get("/")
def root():
    return {
        "message": "WZDM LiveRecord API",
        "version": "0.1.0",
        "docs": "/docs",
    }
