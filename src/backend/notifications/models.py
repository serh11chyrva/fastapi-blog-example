"""Notification sources and recipient-owned groups with monotonic read boundaries."""

from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from backend.auth.client import ClientType

type NotificationKind = Literal["like", "comment", "reply", "repost", "login"]
type SourceKind = Literal["interaction", "comment", "session"]


class NotificationTarget(BaseModel):
    """Reference a publication whose current public visibility controls inbox previews."""

    kind: Literal["micro_post", "article"]
    id: PydanticObjectId


class LoginDetails(BaseModel):
    """Preserve readable client and location labels from the moment of a successful login."""

    client_type: ClientType
    device: str
    location: str


class NotificationEvent(Document):
    """Associate one source action with one recipient and a sequence inside its inbox group."""

    recipient_id: PydanticObjectId
    group_id: PydanticObjectId
    source_kind: SourceKind
    source_id: PydanticObjectId
    actor_id: PydanticObjectId | None = None
    sequence: int
    occurred_at: datetime

    class Settings:
        """Protect source idempotency and support source retraction and group reconstruction."""

        name = "notification_events"
        indexes = [
            IndexModel(
                [("source_kind", ASCENDING), ("source_id", ASCENDING), ("recipient_id", ASCENDING)],
                unique=True, name="notification_source_recipient_unique",
            ),
            IndexModel(
                [("group_id", ASCENDING), ("sequence", DESCENDING)],
                unique=True, name="notification_group_sequence",
            ),
        ]


class NotificationGroup(Document):
    """Store one inbox row, its surviving membership summary, and recipient read boundary."""

    recipient_id: PydanticObjectId
    group_key: str
    kind: NotificationKind
    target: NotificationTarget | None = None
    login: LoginDetails | None = None
    actor_ids: list[PydanticObjectId] = Field(default_factory=list)
    event_count: int = 0
    sequence: int = 0
    latest_sequence: int = 0
    read_through_sequence: int = 0
    is_read: bool = False
    last_event_at: datetime

    class Settings:
        """Index recipient ownership, chronological pages, and unread row counts."""

        name = "notification_groups"
        indexes = [
            IndexModel(
                [("recipient_id", ASCENDING), ("group_key", ASCENDING)],
                unique=True, name="notification_recipient_group_unique",
            ),
            IndexModel(
                [("recipient_id", ASCENDING), ("last_event_at", DESCENDING), ("_id", DESCENDING)],
                name="notification_inbox_page",
            ),
            IndexModel(
                [("recipient_id", ASCENDING), ("is_read", ASCENDING)], name="notification_unread_count",
            ),
        ]
