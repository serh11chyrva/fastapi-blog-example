"""Plain-text discussion requests and distinct flat/threaded response contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.api import examples
from backend.profiles.schemas import ProfileUserResponse


class CommentText(BaseModel):
    """Accept nonblank plain text without attachment or HTML interpretation."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [examples.COMMENT_CREATE]})

    text: str = Field(
        min_length=1,
        max_length=5000,
        description="Plain text, trimmed and nonblank, up to 5,000 characters.",
    )

    @field_validator("text")
    @classmethod
    def trim_text(cls, value: str) -> str:
        """Trim comment text and reject whitespace-only content.

        :param value: Supplied plain-text comment or reply content.
        :return: Nonempty text without surrounding whitespace.
        """
        value = value.strip()

        if not value:
            raise ValueError("Comment text cannot be empty")

        return value


class PostReplyCreate(CommentText):
    """Create a root reply or a child of an undeleted reply in the same post."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.POST_REPLY_CREATE]})

    parent_id: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{24}$",
        description="Live parent reply in this post, or null for a root reply. Immutable after creation.",
    )


class CommentResponse(BaseModel):
    """Public discussion content shared by flat comments and threaded reply responses."""

    id: str
    author: ProfileUserResponse | None
    text: str | None = Field(description="Plain text, or null for a deleted tombstone.")
    created_at: datetime
    updated_at: datetime
    deleted: bool
    likes_count: int = Field(default=0, ge=0, description="Number of likes on the live entry.")
    liked: bool = Field(default=False, description="Whether the current viewer likes this entry.")


class PostReplyResponse(CommentResponse):
    """Thread location plus a direct-child count for loading the next discussion level."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [examples.POST_REPLY, examples.POST_REPLY_CHILD, examples.POST_REPLY_DELETED]},
    )

    post_id: str
    parent_id: str | None
    root_id: str
    depth: int = Field(ge=0, description="Zero for a root reply; each child adds one, without a fixed depth limit.")
    replies_count: int = Field(ge=0, description="Direct children, including tombstones that preserve their branches.")


class ArticleCommentResponse(CommentResponse):
    """Flat article comment with no nesting metadata."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.ARTICLE_COMMENT]})

    article_id: str


class PostReplyPage(BaseModel):
    """One level of a post discussion, ordered oldest first by ObjectId."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.POST_REPLY_PAGE]})

    items: list[PostReplyResponse]
    next_cursor: str | None


class ArticleCommentPage(BaseModel):
    """Flat article comment page, ordered oldest first by ObjectId."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.ARTICLE_COMMENT_PAGE]})

    items: list[ArticleCommentResponse]
    next_cursor: str | None
