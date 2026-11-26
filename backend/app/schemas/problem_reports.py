# Problem report schemas

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ProblemReportRequest(BaseModel):
    client_event_id: Optional[str] = None
    occurred_at: Optional[datetime] = None
    topic: str
    description: Optional[str] = None
    pain_response: Optional[str] = None
    attachment_id: Optional[str] = None
    privacy_scope: str = "PATIENT_PRIVATE"


class ProblemReportResponse(BaseModel):
    report_id: str
    event_id: str
    status: str
    received_at: datetime
    practice_contact: dict
