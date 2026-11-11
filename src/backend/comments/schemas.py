"""Shared publication content and threaded discussion response contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.api import examples
from backend.posts.schemas import MicroPostCreate, MicroPostResponse
from backend.profiles.schemas import ProfileUserResponse


class CommentText(MicroPostCreate):
    """Accept the same text and attachment content as an ordinary post."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [examples.COMMENT_CREATE]})


class PostReplyCreate(CommentText):
    """Create a root reply or a child of an undeleted reply in the same discussion."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.POST_REPLY_CREATE]})

    parent_id: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{24}$",
        description="Live parent reply in this discussion, or null for a root reply. Immutable after creation.",
    )


class CommentResponse(BaseModel):
    """Public discussion content shared by post and article reply responses."""

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

    post_id: str | None = None
    article_id: str | None = None
    publication: MicroPostResponse | None = None
    parent_id: str | None
    root_id: str
    depth: int = Field(ge=0, description="Zero for a root reply; each child adds one, without a fixed depth limit.")
    replies_count: int = Field(ge=0, description="Direct children, including tombstones that preserve their branches.")


class ArticleCommentResponse(PostReplyResponse):
    """Article-rooted reply with the same publication identity and nesting metadata."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.ARTICLE_COMMENT]})

    article_id: str


class PostReplyPage(BaseModel):
    """One level of a post discussion, ordered oldest first by ObjectId."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.POST_REPLY_PAGE]})

    items: list[PostReplyResponse]
    next_cursor: str | None


class ArticleCommentPage(BaseModel):
    """One article discussion level in the requested order."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.ARTICLE_COMMENT_PAGE]})

    items: list[ArticleCommentResponse]
    next_cursor: str | None
