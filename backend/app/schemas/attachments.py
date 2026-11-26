# Attachment schemas

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UploadSlotResponse(BaseModel):
    attachment_id: str
    state: str
    expires_at: datetime


class AccessLinkResponse(BaseModel):
    attachment_id: str
    url: str
    expires_at: datetime


class QuarantineCheckResponse(BaseModel):
    attachment_id: str
    state: str
    checks: List[str]
