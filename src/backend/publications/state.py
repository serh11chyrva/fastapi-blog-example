"""Shared response fields for archive state, profile pins, and interaction access."""

from datetime import datetime

from pydantic import BaseModel, Field


class PublicationState(BaseModel):
    """Expose archive and pin timestamps without changing content edit timestamps."""

    read_only: bool = Field(
        default=False,
        description="True when this response is private or has a private discussion context; "
        "new interactions require public visibility.",
    )

    archived_at: datetime | None = Field(
        default=None,
        description="UTC time of the current archive operation, or null. Archived content is owner-only.",
    )
    pinned_at: datetime | None = Field(
        default=None,
        description="UTC time of the current profile pin, or null. At most five publications per owner may be pinned.",
    )
