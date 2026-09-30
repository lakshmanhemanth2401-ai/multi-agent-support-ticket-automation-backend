from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from app.schemas.pagination import PageMetadata


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    action: str
    details: dict[str, Any] | None
    created_at: datetime


class AuditLogPage(BaseModel):
    items: list[AuditLogRead]
    pagination: PageMetadata
