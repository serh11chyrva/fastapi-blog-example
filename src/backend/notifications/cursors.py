"""Opaque positions in the recipient's mutable grouped notification timeline."""

import base64
from typing import Any, Literal, Self

from beanie import PydanticObjectId
from pydantic import AwareDatetime, BaseModel, ValidationError

from backend.core.errors import InvalidOperation


class NotificationCursor(BaseModel):
    """Represent a descending last-event timestamp and group ObjectId boundary."""

    version: Literal[1] = 1
    time: AwareDatetime
    id: PydanticObjectId

    def encode(self) -> str:
        """Encode the position without exposing cursor structure as a client contract.

        :return: The URL-safe cursor string.
        """
        return base64.urlsafe_b64encode(self.model_dump_json().encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, value: str | None) -> Self | None:
        """Reject malformed, unsupported, or timezone-naive cursor payloads.

        :param value: Previous opaque cursor, or None for the first page.
        :return: The validated position, or None when no cursor was supplied.
        """
        if not value:
            return None
        try:
            return cls.model_validate_json(
                base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True),
            )
        except (ValueError, TypeError, ValidationError) as exc:
            raise InvalidOperation("Invalid notification cursor") from exc

    def conditions(self) -> dict[str, Any]:
        """Continue strictly after this position in descending inbox order.

        :return: MongoDB conditions preserving ties between group timestamps.
        """
        return {"$or": [
            {"last_event_at": {"$lt": self.time}},
            {"last_event_at": self.time, "_id": {"$lt": self.id}},
        ]}
