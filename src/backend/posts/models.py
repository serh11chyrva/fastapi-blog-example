from datetime import datetime
from uuid import uuid4

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from backend.publications.attachments import PublicationAttachments
from backend.publications.models import PublicationAuthors


class MicroPost(Document, PublicationAuthors):
    """Public short-form publication with ordered authors, stable sharing, and typed content attachments."""

    attachments: PublicationAttachments = Field(default_factory=list)
    interaction_revision: int = 0
    share_id: str = Field(default_factory=lambda: uuid4().hex)
    text: str
    image_keys: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    class Settings:
        """Beanie collection and index configuration for MicroPost."""

        name = "micro_posts"
        indexes = [
            IndexModel(
                [("owner_id", ASCENDING), ("created_at", DESCENDING)],
                name="posts_owner_time",
            ),
            IndexModel(
                [("featured_author_ids", ASCENDING), ("created_at", DESCENDING)],
                name="posts_featured_authors_time",
            ),
            IndexModel([("share_id", ASCENDING)], name="posts_share_id"),
            IndexModel(
                [("image_keys", ASCENDING), ("deleted_at", ASCENDING)],
                name="posts_image_attachment",
            ),
            IndexModel(
                [
                    ("deleted_at", ASCENDING),
                    ("created_at", DESCENDING),
                    ("_id", DESCENDING),
                ],
                name="posts_feed_page",
            ),
        ]
