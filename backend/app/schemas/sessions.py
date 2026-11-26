# Session and authentication schemas

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PrincipalResponse(BaseModel):
    actor_type: str
    assurance: str
    active_practice: Optional[str] = None
    permitted_roles: List[str] = []
    linked_patient_contexts: List[dict] = []
    safe_prompts: List[str] = []


class PracticeContextResponse(BaseModel):
    practice_id: str
    membership_id: str
    active: bool
    session_version: int


class SessionRevokeResponse(BaseModel):
    status: str = "revoked"
