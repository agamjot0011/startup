"""
WZDM LiveRecord - Common response schemas.

Pydantic models for API responses shared across the project.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Pagination(BaseModel):
    next_cursor: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    correlation_id: Optional[str] = None


class SafeRoute(BaseModel):
    contact_phone_display: str
    emergency_content_version_id: str
    emergency_wording: str
    monitoring_hours_disclaimer: str


class PracticeSummary(BaseModel):
    practice_id: str
    display_name: str
    timezone: str
    status: str
    contact_phone_display: str
    emergency_content_version_id: Optional[str] = None
    created_at: Optional[datetime] = None
