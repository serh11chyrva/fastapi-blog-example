from datetime import datetime

from beanie import Document, PydanticObjectId
from pydantic import Field, JsonValue
from pymongo import ASCENDING, DESCENDING, IndexModel


class AuditEvent(Document):
    """Append-only security or domain event stored in MongoDB."""

    actor_id: PydanticObjectId | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    occurred_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    class Settings:
        """Beanie collection and index configuration for AuditEvent."""

        name = "audit_events"
        indexes = [
            IndexModel([("occurred_at", DESCENDING)], name="audit_time_desc"),
            IndexModel(
                [("actor_id", ASCENDING), ("occurred_at", DESCENDING)],
                name="audit_actor_time",
            ),
        ]
