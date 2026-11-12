"""Owner archive pages with typed publication cards."""

from pydantic import BaseModel, ConfigDict, Field

from backend.api import examples
from backend.feeds.schemas import ArticleFeedItem, PostFeedItem


class ArchivePage(BaseModel):
    """An owner's archived publications ordered by archive time, kind, and ID."""

    model_config = ConfigDict(json_schema_extra={"examples": [examples.ARCHIVE_PAGE]})

    items: list[PostFeedItem | ArticleFeedItem] = Field(description="Owned archived posts, replies, and articles.")
    next_cursor: str | None = Field(description="Opaque archive continuation cursor, or null when complete.")
