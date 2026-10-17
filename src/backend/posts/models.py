from datetime import datetime
from uuid import uuid4

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel


class MicroPost(Document):
    """Public short-form publication with stable sharing and image attachments."""

    author_id: PydanticObjectId
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
                [("author_id", ASCENDING), ("created_at", DESCENDING)],
                name="posts_author_time",
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
