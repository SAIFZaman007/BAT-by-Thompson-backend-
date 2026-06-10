from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class StatsOut(BaseModel):
    submissions_total: int
    submissions_by_status: dict[str, int]
    kyc_documents_total: int
    submissions_without_kyc: int
    contact_messages_total: int
    submissions_last_7_days: int


class AuditOut(BaseModel):
    id: str
    actor: str
    action: str
    target: str
    created_at: dt.datetime

    model_config = {"from_attributes": True}
