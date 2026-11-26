from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.family import router as family_router
from app.api.routes.patients import router as patients_router
from app.api.routes.attachments import router as attachments_router
from app.api.routes.problem_reports import router as problem_reports_router
from app.api.routes.problem_reports import alias_router as problem_reports_alias_router
from app.api.routes.rules import new_router_alias as new_router_alias
from app.api.routes.content import content_version_alias_router as content_version_alias_router
from app.api.routes.cards import router as cards_router
from app.api.routes.visit_briefs import router as visit_briefs_router
from app.api.routes.visit_briefs import canonical_router as operations_canonical_router
from app.api.routes.imports import router as imports_router
from app.api.routes.rules import router as rules_router
from app.api.routes.content import router as content_router
from app.api.routes.proxy import router as proxy_router
from app.api.routes.consents import router as consents_router
from app.api.routes.support_grants import router as support_grants_router
from app.api.routes.audit import router as audit_router
from app.api.routes.exports import router as exports_router
from app.api.routes.provider_webhooks import router as provider_webhooks_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(sessions_router)
api_router.include_router(family_router)
api_router.include_router(patients_router)
api_router.include_router(attachments_router)
api_router.include_router(problem_reports_router)
api_router.include_router(problem_reports_alias_router)
api_router.include_router(cards_router)
api_router.include_router(visit_briefs_router)
api_router.include_router(operations_canonical_router)
api_router.include_router(imports_router)
api_router.include_router(rules_router)
api_router.include_router(new_router_alias)
api_router.include_router(content_router)
api_router.include_router(content_version_alias_router)
api_router.include_router(proxy_router)
api_router.include_router(consents_router)
api_router.include_router(support_grants_router)
api_router.include_router(audit_router)
api_router.include_router(exports_router)
api_router.include_router(provider_webhooks_router)
