from datetime import datetime
from typing import Literal
from uuid import uuid4

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from backend.articles.validation import ArticleBody
from backend.publications.attachments import PublicationAttachments
from backend.publications.models import PublicationAuthors


class ArticlePreviewSource(PublicationAuthors):
    """Read the persisted fields needed for a public article card."""

    id: PydanticObjectId = Field(alias="_id")
    share_id: str
    title: str
    summary: str = ""
    thumbnail_key: str | None = None
    published_at: datetime


class Article(Document, PublicationAuthors):
    """Long-form publication with ordered authors, a TipTap body, and publication state."""

    attachments: PublicationAttachments = Field(default_factory=list)
    interaction_revision: int = 0
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
                [("owner_id", ASCENDING), ("created_at", DESCENDING)],
                name="articles_owner_time",
            ),
            IndexModel(
                [("status", ASCENDING), ("published_at", DESCENDING)],
                name="articles_public_feed",
            ),
            IndexModel(
                [("status", ASCENDING), ("scheduled_at", ASCENDING)],
                name="articles_scheduled_publish",
            ),
            IndexModel(
                [("featured_author_ids", ASCENDING), ("created_at", DESCENDING)],
                name="articles_featured_authors_time",
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
                    ("owner_id", ASCENDING),
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
