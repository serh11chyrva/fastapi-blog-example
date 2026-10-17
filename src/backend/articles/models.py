from datetime import datetime
from typing import Literal
from uuid import uuid4

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from backend.articles.validation import ArticleBody


class Article(Document):
    """Long-form publication with a TipTap body and draft or publishing state."""

    author_id: PydanticObjectId
    share_id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    summary: str = ""
    body: ArticleBody
    thumbnail_key: str | None = None
    inline_image_keys: list[str] = Field(default_factory=list)
    status: Literal["draft", "scheduled", "published"] = "draft"
    created_at: datetime
    updated_at: datetime
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    deleted_at: datetime | None = None

    class Settings:
        """Beanie collection and index configuration for Article."""

        name = "articles"
        indexes = [
            IndexModel(
                [("author_id", ASCENDING), ("created_at", DESCENDING)],
                name="articles_author_time",
            ),
            IndexModel(
                [("status", ASCENDING), ("published_at", DESCENDING)],
                name="articles_public_feed",
            ),
            IndexModel(
                [("status", ASCENDING), ("scheduled_at", ASCENDING)],
                name="articles_scheduled_publish",
            ),
            IndexModel([("share_id", ASCENDING)], name="articles_share_id"),
            IndexModel(
                [("thumbnail_key", ASCENDING), ("deleted_at", ASCENDING)],
                name="articles_cover_attachment",
            ),
            IndexModel(
                [("inline_image_keys", ASCENDING), ("deleted_at", ASCENDING)],
                name="articles_inline_attachment",
            ),
            IndexModel(
                [
                    ("author_id", ASCENDING),
                    ("deleted_at", ASCENDING),
                    ("updated_at", DESCENDING),
                    ("_id", DESCENDING),
                ],
                name="articles_owner_page",
            ),
            IndexModel(
                [
                    ("status", ASCENDING),
                    ("deleted_at", ASCENDING),
                    ("published_at", DESCENDING),
                    ("_id", DESCENDING),
                ],
                name="articles_feed_page",
            ),
        ]
