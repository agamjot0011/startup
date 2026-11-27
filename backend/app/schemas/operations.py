# Visit brief and operations schemas

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class VisitBriefResponse(BaseModel):
    appointment_id: str
    source_watermark: str
    projection_generated_at: datetime
    events_since_cutoff: List[dict] = []
    assistant_captures: List[dict] = []
    open_cards: List[dict] = []
    row_version: int = Field(alias="rowVersion")


class HuddleResponse(BaseModel):
    huddle_date: str
    open_cards: List[dict] = []
    overdue_cards: List[dict] = []
    closed_cards: List[dict] = []
    import_freshness: str
    practice: str


class LoopReportResponse(BaseModel):
    date: str
    open_loops: List[dict] = []
    overdue_loops: List[dict] = []
    closed_loops: List[dict] = []
    report_generated_at: datetime


class AlertBudgetResponse(BaseModel):
    budget: dict
    quiet_hours: dict
    dismissed: List[str] = []
