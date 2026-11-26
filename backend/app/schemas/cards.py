# Card and loop schemas

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CardResponse(BaseModel):
    card_id: str
    card_type: str
    status: str
    owner: Optional[str] = None
    deadline_at: datetime
    loop_id: Optional[str] = None
    row_version: int = Field(alias="rowVersion")


class CardDetailResponse(BaseModel):
    card_id: str
    card_type: str
    what_happened: str
    meaning_for_role: str
    look_for: List[str] = []
    action: str
    by_when: str
    owner: Optional[str] = None
    deadline_at: datetime
    status: str
    privacy_scope: str
    row_version: int = Field(alias="rowVersion")


class CardActionResponse(BaseModel):
    acknowledgement_id: Optional[str] = None
    card_id: str
    status: str
    row_version: int = Field(alias="rowVersion")


class LoopResponse(BaseModel):
    loop_id: str
    trigger: str
    mandatory_cards: List[str] = []
    advisory_cards: List[str] = []
    status: str
    operational_closure: bool = False
    clinical_outcome: Optional[str] = None
