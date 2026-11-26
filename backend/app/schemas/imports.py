# Import schemas

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ImportBatchResponse(BaseModel):
    import_id: str
    state: str
    source: str
    batch_id: Optional[str] = None
    row_counts: dict = {}
    pending_reconciliation: List[dict] = []


class ImportCommitResponse(BaseModel):
    import_id: str
    state: str
    committed_at: datetime
    counts: dict
