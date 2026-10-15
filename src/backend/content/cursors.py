"""Opaque feed cursors ordered by timestamp, publication kind, and ObjectId."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from pydantic import AwareDatetime, BaseModel, ValidationError

from backend.content.repository import PublicationKind
from backend.core.errors import InvalidOperation


class CursorPayload(BaseModel):
    time: AwareDatetime
    kind: PublicationKind
    id: PydanticObjectId


@dataclass(frozen=True, slots=True)
class FeedCursor:
    published_at: datetime
    kind: PublicationKind
    object_id: PydanticObjectId

    def encode(self) -> str:
        payload = CursorPayload(time=self.published_at, kind=self.kind, id=self.object_id)
        return base64.urlsafe_b64encode(payload.model_dump_json().encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, value: str | None) -> FeedCursor | None:
        """Read an existing cursor; malformed or timezone-naive payloads are rejected."""
        if not value:
            return None
        try:
            payload = CursorPayload.model_validate_json(base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True))
        except (ValueError, TypeError, ValidationError) as exc:
            raise InvalidOperation("Invalid feed cursor") from exc
        return cls(payload.time, payload.kind, payload.id)

    def conditions(self, kind: PublicationKind, date_field: str) -> dict[str, Any]:
        """Continue descending order across collections, including equal timestamps."""
        if kind < self.kind:
            return {date_field: {"$lte": self.published_at}}
        if kind > self.kind:
            return {date_field: {"$lt": self.published_at}}
        return {"$or": [
            {date_field: {"$lt": self.published_at}},
            {date_field: self.published_at, "_id": {"$lt": self.object_id}},
        ]}
