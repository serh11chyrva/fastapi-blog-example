from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.api import examples
from backend.links.schemas import LinkPresentation
from backend.posts.models import ReplyMetadata
from backend.posts.schemas import ReplyTombstone
from backend.profiles.schemas import ProfileUserResponse
from backend.publications.attachments import PublicationAttachment
from backend.publications.state import PublicationState


class FeedBase(LinkPresentation, PublicationState):
    """Shared author, visibility, and date fields for a public or owner-only archive card."""

    model_config = ConfigDict(
        title="Feed publication",
        json_schema_extra={"examples": [examples.FEED_ARTICLE, examples.FEED_POST]},
    )

    attachments: list[PublicationAttachment] = Field(
        default_factory=list, description="Typed publication attachments, including uploaded images without placement."
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
    published_at: datetime = Field(
        description="UTC publication time used for feed ordering; creation time for micro-posts.",
        examples=[examples.ARTICLE_PUBLISHED["published_at"]],
    )
    updated_at: datetime | None = Field(
        default=None,
        description="UTC time the original publication was last updated, if available.",
        examples=[examples.POST["updated_at"]],
    )


class PostCard(FeedBase):
    """Nonrecursive post card with no embedded thread or personalized interaction state."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.FEED_POST]})

    kind: Literal["micro_post"] = "micro_post"
    reply: ReplyMetadata | None = None
    text: str = Field(description="Micro-post text; archived cards are owner-only.")
    title: None = None
    summary: None = None
    thumbnail_url: None = None


ThreadPart = Annotated[PostCard | ReplyTombstone, Field(discriminator="kind")]


class ThreadPreview(BaseModel):
    """Up to two continuations, making at most three displayed parts with their root."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.THREAD_PREVIEW]})

    parts: list[ThreadPart] = Field(max_length=2, description="Author continuations in ascending creation order.")
    has_more: bool = Field(description="Whether the full thread contains additional continuations.")


class PostFeedItem(PostCard):
    """Post card optionally enriched with its automatic author-thread preview."""

    model_config = ConfigDict(json_schema_extra={"examples": [
        examples.FEED_POST, examples.FEED_POST | {"thread_preview": examples.THREAD_PREVIEW},
    ]})

    thread_preview: ThreadPreview | None = Field(
        default=None, description="Only standalone originals in grouped lists carry an author-thread preview.",
    )


class AuthorThreadPage(BaseModel):
    """Original post and one ascending page of connected author continuations."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.AUTHOR_THREAD_PAGE]})

    root: PostCard
    items: list[ThreadPart]
    next_cursor: str | None = Field(description="Root-bound continuation cursor, or null at the end.")


class ArticleFeedItem(FeedBase):
    """Compact article representation returned in publication feeds."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.FEED_ARTICLE]})

    kind: Literal["article"] = "article"
    comments_enabled: bool = Field(default=True, description="Whether the article discussion is visible and accepts replies.")
    title: str = Field(description="Article title; archived cards are owner-only.")
    summary: str = Field(description="Article preview; may be empty.")
    thumbnail_url: str | None = Field(default=None, description="Article cover URL, if present.")
    text: None = None


class RepostFeedItem(BaseModel):
    """A public repost event retaining the original post and its original author credits."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.FEED_REPOST]})

    id: str = Field(description="Repost relationship identifier, distinct from the original post ID.")
    kind: Literal["repost"] = "repost"
    reposted_by: ProfileUserResponse
    published_at: datetime = Field(description="UTC repost time used to position this event in feeds.")
    post: PostFeedItem = Field(description="Currently public original post, with its own ID, authors, and attachments.")


class RepostPage(BaseModel):
    """An account's public repost history, ordered by relationship ID descending."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.REPOST_PAGE]})

    items: list[RepostFeedItem]
    next_cursor: str | None


FeedItem = Annotated[PostFeedItem | ArticleFeedItem | RepostFeedItem, Field(discriminator="kind")]


class ArticlePreview(BaseModel):
    """Public article card without the body or nested attachments."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.ARTICLE_PREVIEW]})

    kind: Literal["article"] = "article"
    id: str
    share_url: str
    authors: list[ProfileUserResponse]
    title: str
    summary: str
    thumbnail_url: str | None
    published_at: datetime


class PostPreview(BaseModel):
    """Public post card without nested publication references."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.POST_PREVIEW]})

    kind: Literal["micro_post"] = "micro_post"
    id: str
    share_url: str
    authors: list[ProfileUserResponse]
    text: str
    thumbnail_url: str | None
    published_at: datetime
    updated_at: datetime = Field(
        description="UTC time the original post was last updated.",
        examples=[examples.POST["updated_at"]],
    )


PublicationPreview = Annotated[ArticlePreview | PostPreview, Field(discriminator="kind")]


ProfileTimelineItem = Annotated[PostFeedItem | RepostFeedItem, Field(discriminator="kind")]


class ProfileTimelinePage(BaseModel):
    """Chronological profile activity page, newest first."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.PROFILE_TIMELINE]})

    items: list[ProfileTimelineItem]
    next_cursor: str | None


class FeedResponse(BaseModel):
    """Chronological page. Pass `next_cursor` back to continue."""

    model_config = ConfigDict(title="Feed page", json_schema_extra={"examples": [examples.FEED]})

    items: list[FeedItem] = Field(
        description="Public original publications and repost events, newest first. Article bodies are fetched separately.",
        examples=[[examples.FEED_REPOST, examples.FEED_ARTICLE, examples.FEED_POST]],
    )
    next_cursor: str | None = Field(
        description="Opaque pagination cursor. Pass unchanged as cursor with the same kind filter; null means there are no more results.",
        examples=[examples.CURSOR, None],
    )
