from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.family import router as family_router
from app.api.routes.patients import router as patients_router
from app.api.routes.attachments import router as attachments_router
from app.api.routes.problem_reports import router as problem_reports_router
from app.api.routes.cards import router as cards_router
from app.api.routes.visit_briefs import router as visit_briefs_router
from app.api.routes.imports import router as imports_router
from app.api.routes.rules import router as rules_router
from app.api.routes.content import router as content_router
from app.api.routes.proxy import router as proxy_router
from app.api.routes.consents import router as consents_router
from app.api.routes.support_grants import router as support_grants_router
from app.api.routes.audit import router as audit_router
from app.api.routes.exports import router as exports_router
from app.api.routes.provider_webhooks import router as provider_webhooks_router
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

# Register all API routers
app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(family_router)
app.include_router(patients_router)
app.include_router(attachments_router)
app.include_router(problem_reports_router)
app.include_router(cards_router)
app.include_router(visit_briefs_router)
app.include_router(imports_router)
app.include_router(rules_router)
app.include_router(content_router)
app.include_router(proxy_router)
app.include_router(consents_router)
app.include_router(support_grants_router)
app.include_router(audit_router)
app.include_router(exports_router)
app.include_router(provider_webhooks_router)


@app.get("/")
def root():
    return {
        "message": "WZDM LiveRecord API",
        "version": "0.1.0",
        "docs": "/docs",
    }
