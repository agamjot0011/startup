# Patient and relationship schemas

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PatientResponse(BaseModel):
    patient_id: str
    status: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    birth_date: Optional[str] = None
    locale: str = "en"
    timezone: str = "UTC"
    created_at: Optional[datetime] = None


class PatientHomeResponse(BaseModel):
    patient_id: str
    safe_route: Optional[SafeRoute] = None
    today_card_summary: List[dict] = []
    next_visit_summary: Optional[dict] = None
    unread_count: int = 0


class TimelineEventResponse(BaseModel):
    event_id: str
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    privacy_scope: str


class TimelineResponse(BaseModel):
    events: List[TimelineEventResponse] = []
    next_cursor: Optional[str] = None


class IdentifiersResponse(BaseModel):
    patient_id: str
    source_system: str
    external_id: str
    valid_from: datetime
    valid_to: Optional[datetime] = None


class PatientUserLinkResponse(BaseModel):
    patient_id: str
    user_id: str
    status: str
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class ProxyRelationshipResponse(BaseModel):
    relationship_id: str
    patient_id: str
    relationship_code: str
    authority_scopes: List[str]
    verification_method: str
    policy_version_id: Optional[str] = None
    status: str
    effective_from: datetime
    effective_to: Optional[datetime] = None


class ConsentResponse(BaseModel):
    consent_id: str
    patient_id: str
    consent_kind: str
    decision: str
    source_content_version_id: Optional[str] = None
    effective_from: datetime
    effective_to: Optional[datetime] = None


class PrivacySummaryResponse(BaseModel):
    relationship: Optional[ProxyRelationshipResponse] = None
    consent: Optional[ConsentResponse] = None
    channel: dict = {}
