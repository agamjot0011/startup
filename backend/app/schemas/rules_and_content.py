# Rule and content schemas

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RuleSetResponse(BaseModel):
    rule_set_id: str
    semantic_key: str
    trigger_event: str
    active_version_id: Optional[str] = None


class RuleVersionResponse(BaseModel):
    rule_version_id: str
    version_number: int
    state: str
    checksum: str


class ContentItemResponse(BaseModel):
    content_item_id: str
    semantic_key: str
    content_class: str
    audience: str
    purpose: str


class ContentVersionResponse(BaseModel):
    version_id: str
    version_number: int
    locale: str
    state: str
    checksum: str


class ContentDetailResponse(BaseModel):
    content_version_id: str
    version_number: int
    locale: str
    state: str
    body: dict
    checksum: str
    readability: Optional[str] = None
