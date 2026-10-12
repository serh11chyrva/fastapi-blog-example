from datetime import datetime
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel


class AuditEvent(Document):
    actor_id: PydanticObjectId | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    occurred_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "audit_events"
        indexes = [
            IndexModel([("occurred_at", DESCENDING)], name="audit_time_desc"),
            IndexModel([("actor_id", ASCENDING), ("occurred_at", DESCENDING)], name="audit_actor_time"),
        ]
