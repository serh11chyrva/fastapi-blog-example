from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.api import examples


class FeedBase(BaseModel):
    """Shared author and ordering data for a public feed entry."""

    model_config = ConfigDict(
        title="Feed publication",
        json_schema_extra={"examples": [examples.FEED_ARTICLE, examples.FEED_POST]},
    )

    id: str = Field(
        description="Publication identifier; use kind to select the post or article endpoint.",
        examples=[examples.ARTICLE["id"]],
    )
    share_url: str | None = Field(
        default=None,
        description="Relative URL of the public publication page.",
        examples=[examples.ARTICLE["share_url"]],
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
    published_at: datetime = Field(
        description="UTC publication time used for feed ordering; creation time for micro-posts.",
        examples=[examples.ARTICLE_PUBLISHED["published_at"]],
    )


class PostFeedItem(FeedBase):
    """Compact micro-post representation returned in publication feeds."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.FEED_POST]})

    kind: Literal["micro_post"] = "micro_post"
    text: str = Field(description="Public micro-post text.")
    images: list[str] = Field(default_factory=list, description="Post image URLs in display order.")
    title: None = None
    summary: None = None
    thumbnail_url: None = None


class ArticleFeedItem(FeedBase):
    """Compact article representation returned in publication feeds."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.FEED_ARTICLE]})

    kind: Literal["article"] = "article"
    title: str = Field(description="Public article title.")
    summary: str = Field(description="Article preview; may be empty.")
    thumbnail_url: str | None = Field(default=None, description="Article cover URL, if present.")
    text: None = None
    images: list[str] = Field(default_factory=list, max_length=0)


FeedItem = Annotated[PostFeedItem | ArticleFeedItem, Field(discriminator="kind")]


class FeedResponse(BaseModel):
    """Chronological page. Pass `next_cursor` back to continue."""

    model_config = ConfigDict(title="Feed page", json_schema_extra={"examples": [examples.FEED]})

    items: list[FeedItem] = Field(
        description="Public publications ordered newest first. May be empty; article bodies are fetched separately.",
        examples=[[examples.FEED_ARTICLE, examples.FEED_POST]],
    )
    next_cursor: str | None = Field(
        description="Opaque pagination cursor. Pass unchanged as cursor with the same kind filter; null means there are no more results.",
        examples=[examples.CURSOR, None],
    )
