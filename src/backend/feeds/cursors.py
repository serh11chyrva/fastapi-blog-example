"""Opaque feed cursors ordered by event time, original/repost kind, and event ObjectId."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from beanie import PydanticObjectId
from pydantic import AwareDatetime, BaseModel, ValidationError

from backend.core.errors import InvalidOperation
from backend.feeds.repository import PublicationKind

type TimelineKind = PublicationKind | Literal["article_comment"]


class CursorPayload(BaseModel):
    """Validated position supporting original publications and independent repost events."""

    time: AwareDatetime
    kind: TimelineKind
    id: PydanticObjectId


@dataclass(frozen=True, slots=True)
class FeedCursor:
    """Stable feed position ordered by event time, event kind, and original or repost ID."""

    published_at: datetime
    kind: TimelineKind
    object_id: PydanticObjectId

    def encode(self) -> str:
        """Encode the feed position as an opaque URL-safe cursor.

        :return: The encoded cursor string.
        """
        payload = CursorPayload(time=self.published_at, kind=self.kind, id=self.object_id)

        return base64.urlsafe_b64encode(payload.model_dump_json().encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, value: str | None, *, profile: bool = False) -> FeedCursor | None:
        """Read an existing cursor; malformed or timezone-naive payloads are rejected.

        :param value: Opaque feed cursor, or None for the initial page.
        :param profile: Whether profile-only comment positions are accepted.
        :return: The decoded cursor, or None when no cursor was supplied.
        """
        if not value:
            return None

        try:
            payload = CursorPayload.model_validate_json(
                base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
            )
        except (ValueError, TypeError, ValidationError) as exc:
            raise InvalidOperation("Invalid feed cursor") from exc

        if payload.kind == "article_comment" and not profile:
            raise InvalidOperation("Invalid feed cursor")

        return cls(payload.time, payload.kind, payload.id)

    def conditions(self, kind: TimelineKind, date_field: str) -> dict[str, Any]:
        """Continue descending order across collections, including equal timestamps.

        :param kind: Original publication or repost event kind whose boundary is being computed.
        :param date_field: MongoDB timestamp field used to order this original collection or repost edge.
        :return: MongoDB filters selecting entries strictly after this cursor.
        """
        if kind < self.kind:
            return {date_field: {"$lte": self.published_at}}

        if kind > self.kind:
            return {date_field: {"$lt": self.published_at}}

        return {
            "$or": [
                {date_field: {"$lt": self.published_at}},
                {date_field: self.published_at, "_id": {"$lt": self.object_id}},
            ]
        }
