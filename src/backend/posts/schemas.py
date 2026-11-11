from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.api import examples
from backend.posts.models import ReplyMetadata
from backend.profiles.schemas import ProfileUserResponse
from backend.publications.attachments import PublicationAttachment, PublicationAttachments


class PostDraftRequest(BaseModel):
    """Client-generated retry key for an owner-only upload staging post."""

    model_config = ConfigDict(extra="forbid")
    key: UUID


class MicroPostCreate(BaseModel):
    """Text and optional ordered attachments for a public micro-post."""

    model_config = ConfigDict(
        title="Micro-post content", extra="forbid",
        json_schema_extra={"examples": [examples.POST_CREATE, examples.POST_RICH_CREATE]},
    )

    attachments: PublicationAttachments = Field(
        default_factory=list,
        description="One attachment choice: up to five gallery images, or one player, card, or publication. "
        "Video is reserved and rejected. On edit, omission preserves attachments; [] clears explicit descriptors.",
    )
    text: str = Field(
        default="",
        max_length=280,
        description="Post text, up to 280 characters. Blank text requires an attachment in the final saved state.",
        examples=[examples.POST_TEXT],
    )

    retain_image_urls: list[str] | None = Field(
        default=None, max_length=5, description="On edit, keep only these owned gallery images; [] removes all.",
    )
    image_draft_id: str | None = Field(
        default=None, pattern=r"^[0-9a-fA-F]{24}$",
        description="Owned private staging post whose images atomically replace this gallery on save.",
    )
    expected_updated_at: datetime | None = Field(
        default=None, description="On edit, reject a stale draft with 409 instead of overwriting newer changes.",
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        """Trim micro-post text; final-state validation requires text or an attachment.

        :param value: Micro-post text to trim.
        :return: The trimmed micro-post text, possibly empty.
        """
        value = value.strip()

        return value


class MicroPostResponse(BaseModel):
    """Public post or owner-only staging response with typed attachments and ordered authors."""

    model_config = ConfigDict(
        title="Published micro-post",
        json_schema_extra={"examples": [examples.POST_WITH_IMAGES, examples.POST_WITH_FEATURED_AUTHORS, examples.POST_WITH_CONTENT]},
    )

    reply: ReplyMetadata | None = Field(default=None, description="Immutable discussion context, or null for a post.")
    pending: bool = Field(default=False, description="True only for a private upload draft returned to its owner.")

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
    attachments: list[PublicationAttachment] = Field(
        default_factory=list,
        description="Ordered typed descriptors followed by uploaded images without explicit placement. "
        "Images appear only here as type=image entries, with up to five uploaded images per post. "
        "Resolve account and article IDs through their endpoints to apply current visibility rules.",
    )
    text: str = Field(
        description="Public post text, without surrounding whitespace.",
        examples=[examples.POST_TEXT],
    )
    owner_id: str = Field(
        description="Account owning the publication and controlling edits, uploads, and private visibility.",
        examples=[examples.ACCOUNT["id"]],
    )
    authors: list[ProfileUserResponse] = Field(
        min_length=1,
        description=(
            "Public author cards: owner first, then featured authors in stored order. "
            "Featured authors receive no ownership or private-access rights."
        ),
        examples=[[examples.AUTHOR]],
    )
    created_at: datetime = Field(
        description="UTC publication time, or reservation time while pending. Finalizing a draft resets this time.",
        examples=[examples.POST["created_at"]],
    )
    updated_at: datetime = Field(
        description="UTC time of the most recent text, attachment, or image update.",
        examples=[examples.POST_WITH_IMAGES["updated_at"]],
    )
