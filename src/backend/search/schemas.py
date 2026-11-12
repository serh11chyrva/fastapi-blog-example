"""Public search contracts containing current profiles and publication cards."""

from pydantic import BaseModel, ConfigDict, Field

from backend.api import examples
from backend.feeds.schemas import ArticleFeedItem, PostFeedItem
from backend.profiles.schemas import ProfileUserResponse


class SearchUser(ProfileUserResponse):
    """Public profile search card with a biography and no account-private fields."""

    model_config = ConfigDict(title="Search profile card", json_schema_extra={
        "examples": examples.SEARCH_USERS_PAGE["items"],
    })
    bio: str = Field(description="Current public biography; hashtags link to exact-tag search.")


class SearchUsersPage(BaseModel):
    """Independent cursor page of matching public profiles."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.SEARCH_USERS_PAGE]})
    items: list[SearchUser] = Field(description="Matching public profiles ordered by relevance.")
    next_cursor: str | None = Field(description="Opaque continuation for this user query, or null when complete.")


class SearchPublicationHit(BaseModel):
    """One canonical publication card and an optional current article passage."""

    publication: PostFeedItem | ArticleFeedItem = Field(description="Currently public post, reply, or article.")
    excerpt: str | None = Field(
        default=None,
        description="Plain text of up to 280 characters from the current article body, or null for its preview.",
    )


class SearchPublicationsPage(BaseModel):
    """Mixed original-publication search page with no repost duplicates."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.SEARCH_PUBLICATIONS_PAGE]})
    items: list[SearchPublicationHit] = Field(description="Visible matches in relevance or latest order.")
    next_cursor: str | None = Field(description="Opaque continuation bound to this query and sort, or null when complete.")
