from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from backend.links.platforms import validate_link_url


class LinkData(BaseModel):
    """Versioned profile link label and validated destination URL."""

    version: Literal[1] = Field(default=1, description="Link format version, independent of profile revision.")
    label: str = Field(min_length=1, max_length=32, description="Nonblank public link label.")
    url: str = Field(
        min_length=8,
        max_length=500,
        description="Absolute HTTP(S) destination without credentials or whitespace.",
    )

    @field_validator("label", mode="before")
    @classmethod
    def trim_label(cls, value: str) -> str:
        """Strip surrounding whitespace from a profile link label.

        :param value: Raw profile link label before field validation.
        :return: The trimmed label, or the unchanged input for non-string values.
        """
        return value.strip() if isinstance(value, str) else value

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        """Validate a profile link destination without rewriting its URL.

        :param value: Absolute HTTP or HTTPS profile link destination.
        :return: The validated HTTP or HTTPS URL.
        """
        return validate_link_url(value)


class ProfileLink(LinkData):
    """Embedded profile link with a stable identity independent of its owner handle."""

    id: str = Field(default_factory=lambda: str(uuid4()))

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        """Normalize an embedded link identity to its UUID representation.

        :param value: String representation of the saved link UUID.
        :return: The normalized UUID string.
        """
        return str(UUID(value))
