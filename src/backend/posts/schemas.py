from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.api import examples


class MicroPostCreate(BaseModel):
    """Text for a public micro-post; whitespace-only values are rejected."""

    model_config = ConfigDict(title="Micro-post text", json_schema_extra={"examples": [examples.POST_CREATE]})

    text: str = Field(
        min_length=1,
        max_length=280,
        description="Complete post text, up to 280 characters. Surrounding whitespace is trimmed; blank text is rejected.",
        examples=[examples.POST_TEXT],
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        """Trim micro-post text and reject whitespace-only input.

        :param value: Micro-post text to trim and require to be nonblank.
        :return: The trimmed nonempty micro-post text.
        """
        value = value.strip()

        if not value:
            raise ValueError("Post text cannot be empty")

        return value


class MicroPostResponse(BaseModel):
    """Published micro-post with its public author card."""

    model_config = ConfigDict(
        title="Published micro-post",
        json_schema_extra={"examples": [examples.POST_WITH_IMAGES]},
    )

    id: str = Field(
        description="Post identifier: a 24-character MongoDB ObjectId.",
        examples=[examples.POST["id"]],
    )
    kind: Literal["micro_post"] = Field(
        default="micro_post",
        description="Publication type; always micro_post.",
        examples=["micro_post"],
    )
    share_url: str | None = Field(
        default=None,
        description="Relative public page URL containing the author handle, readable slug, and stable share UUID.",
        examples=[examples.POST["share_url"]],
    )
    text: str = Field(
        description="Public post text, without surrounding whitespace.",
        examples=[examples.POST_TEXT],
    )
    images: list[str] = Field(
        default_factory=list,
        description="Same-origin URLs for attached images, in display order. A post can have up to five images.",
        examples=[[examples.POST_IMAGE_URL]],
    )
    author_id: str = Field(description="Author account identifier.", examples=[examples.ACCOUNT["id"]])
    author_username: str = Field(
        description="Author public handle without @.",
        examples=[examples.ACCOUNT["username"]],
    )
    author_display_name: str = Field(
        description="Author public display name.",
        examples=[examples.ACCOUNT["display_name"]],
    )
    author_avatar_url: str | None = Field(
        description="Author avatar URL, or null when absent.",
        examples=[examples.AVATAR_URL],
    )
    created_at: datetime = Field(
        description="UTC creation time; micro-posts become public immediately.",
        examples=[examples.POST["created_at"]],
    )
    updated_at: datetime = Field(
        description="UTC time of the most recent text or image update.",
        examples=[examples.POST_WITH_IMAGES["updated_at"]],
    )
