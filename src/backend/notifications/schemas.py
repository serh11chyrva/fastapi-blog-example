"""Typed private inbox responses and version-bounded read requests."""

from datetime import datetime
from typing import Annotated, Literal

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

from backend.auth.client import ClientType
from backend.profiles.schemas import ProfileUserResponse

SOCIAL_EXAMPLE = {
    "id": "68ebd423f2b7a8c901234564", "kind": "like", "version": 3, "is_read": False,
    "last_event_at": "2026-11-13T10:10:00Z", "event_count": 2,
    "actors": [{
        "id": "68eb7491d37a2f06b8ce9540", "username": "elliot_gray", "display_name": "Elliot Gray",
        "avatars": {"original": None},
    }],
    "target": {
        "kind": "micro_post", "id": "68eb856f7a02c1349de6b580", "available": True,
        "label": "post", "url": "/posts/68eb856f7a02c1349de6b580", "preview": "A reading note.",
    },
}
LOGIN_EXAMPLE = {
    "id": "68ebd423f2b7a8c901234565", "kind": "login", "version": 1, "is_read": False,
    "last_event_at": "2026-11-13T10:20:00Z",
    "login": {"client_type": "web", "device": "Chrome on Windows", "location": "Kyiv, Ukraine"},
    "url": "/settings/sessions",
}


class NotificationBase(BaseModel):
    """Expose the stable row identity and latest surviving event version used by read receipts."""

    id: str = Field(description="Stable recipient-owned group ObjectId; not an authorization token.")
    version: int = Field(ge=1, description="Latest surviving event sequence; send as through_version after viewing.")
    is_read: bool = Field(description="True when no surviving event lies beyond this row's read boundary.")
    last_event_at: datetime = Field(description="UTC time of the latest surviving event; determines inbox order.")


class NotificationTargetResponse(BaseModel):
    """Expose current public content or a reference-only unavailable placeholder."""

    kind: Literal["micro_post", "article"] = Field(description="Referenced publication collection.")
    id: str = Field(description="Referenced publication ObjectId, retained when unavailable.")
    available: bool = Field(description="Whether the current publication and its discussion path are public.")
    label: Literal["post", "comment", "article", "publication"] = Field(description="Readable target category.")
    url: str | None = Field(description="Same-origin reading path; null for unavailable content.")
    preview: str | None = Field(description="Current plain-text excerpt, at most 240 characters; null if unavailable.")


class SocialNotification(NotificationBase):
    """Present an individual comment/reply or a UTC-day group of active likes/reposts."""

    model_config = ConfigDict(json_schema_extra={"examples": [SOCIAL_EXAMPLE]})

    kind: Literal["like", "comment", "reply", "repost"] = Field(description="Social notification category.")
    event_count: int = Field(ge=1, description="Number of surviving actions in this row, including unavailable actors.")
    actors: list[ProfileUserResponse] = Field(max_length=3, description="Up to three recent current public actor cards.")
    target: NotificationTargetResponse = Field(description="Current authorized target or a content-free placeholder.")


class LoginNotificationDetails(BaseModel):
    """Expose immutable readable labels captured at login without raw request metadata."""

    client_type: ClientType = Field(description="Client category saved when the session was created.")
    device: str = Field(description="Browser/OS or native device label captured at login.")
    location: str = Field(description="Approximate login location; Unknown location when unavailable.")


class LoginNotification(NotificationBase):
    """Present a successful login independently of later session changes or revocation."""

    model_config = ConfigDict(json_schema_extra={"examples": [LOGIN_EXAMPLE]})

    kind: Literal["login"] = Field(description="Successful-login system notification.")
    login: LoginNotificationDetails = Field(description="Readable metadata captured at login.")
    url: Literal["/settings/sessions"] = Field(default="/settings/sessions", description="Session management page.")


type NotificationItem = Annotated[SocialNotification | LoginNotification, Field(discriminator="kind")]


class NotificationPage(BaseModel):
    """Page private inbox rows in descending last-event time and group ID order."""

    model_config = ConfigDict(json_schema_extra={"examples": [{
        "items": [LOGIN_EXAMPLE, SOCIAL_EXAMPLE], "next_cursor": None,
    }]})

    items: list[NotificationItem] = Field(description="Recipient-owned rows, newest activity first.")
    next_cursor: str | None = Field(description="Opaque continuation position; null at the end of the inbox.")


class NotificationSummary(BaseModel):
    """Count unread inbox rows, treating a group of several events as one row."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"unread_count": 3}]})

    unread_count: int = Field(ge=0, description="Unread rows, including rows with unavailable targets.")


class NotificationReadItem(BaseModel):
    """Mark only the events represented by an observed version of an owned row."""

    model_config = ConfigDict(extra="forbid")

    id: PydanticObjectId = Field(description="Group ID from your inbox; missing or foreign IDs are ignored.")
    through_version: int = Field(ge=1, le=2**63 - 1, description="Observed version; never advances beyond issued events.")


class NotificationReadRequest(BaseModel):
    """Batch at most fifty version-bounded recipient read receipts."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [{
        "items": [{"id": SOCIAL_EXAMPLE["id"], "through_version": 3}],
    }]})

    items: list[NotificationReadItem] = Field(min_length=1, max_length=50, description="Viewed group versions.")
