"""Public counts, viewer state, and paginated private/public interaction lists."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from backend.api import examples
from backend.feeds.schemas import ArticleFeedItem, PostFeedItem


class InteractionSummary(BaseModel):
    """Public live counts and the current viewer's private interaction state."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.POST_INTERACTIONS, examples.ARTICLE_INTERACTIONS]})

    likes_count: int = Field(ge=0, description="Number of accounts currently liking this publication.")
    comments_count: int = Field(ge=0, description="Undeleted comments or replies, including all post reply levels.")
    reposts_count: int | None = Field(default=None, ge=0, description="Post repost count; null for articles.")
    liked: bool = Field(description="Whether the current viewer likes this publication; false when anonymous.")
    saved: bool = Field(description="Private save state for this viewer; false when anonymous. No save count is public.")
    reposted: bool | None = Field(default=None, description="Viewer's post repost state; null for articles.")


class SavedPublication(BaseModel):
    """One private saved-publication entry with its currently visible original."""

    id: str = Field(description="Save relationship ID used for list pagination.")
    saved_at: datetime
    publication: Annotated[PostFeedItem | ArticleFeedItem, Field(discriminator="kind")]


class SavedPage(BaseModel):
    """Private saved entries ordered by relationship ObjectId descending."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.SAVED_PAGE]})

    items: list[SavedPublication]
    next_cursor: str | None = Field(description="Pass unchanged to continue; hidden originals may produce empty pages.")
