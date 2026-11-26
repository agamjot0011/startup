# Proxy, consent, support grant schemas

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ProxyRelationshipRequest(BaseModel):
    patient_id: str
    relationship_code: str
    authority_scopes: List[str]
    verification_method: str
    policy_version_id: Optional[str] = None


class ProxyRelationshipResponse(BaseModel):
    relationship_id: str
    patient_id: str
    relationship_code: str
    authority_scopes: List[str]
    status: str
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class ConsentRequest(BaseModel):
    patient_id: str
    consent_kind: str
    decision: str
    signer_authority: str
    source_content_version_id: Optional[str] = None
    locale: str = "en"
    effective_from: Optional[datetime] = None


class ConsentResponse(BaseModel):
    consent_id: str
    patient_id: str
    consent_kind: str
    decision: str
    effective_from: datetime
    effective_to: Optional[datetime] = None


class SupportGrantRequest(BaseModel):
    practice_id: str
    support_user_id: str
    ticket_reference: Optional[str] = None
    purpose_code: str
    scope_json: dict = {}


class SupportGrantResponse(BaseModel):
    grant_id: str
    purpose_code: str
    scope_json: dict
    status: str
    effective_from: datetime
    effective_to: Optional[datetime] = None
