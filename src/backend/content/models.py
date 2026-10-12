from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel


class MicroPost(Document):
    author_id: PydanticObjectId
    share_id: str = Field(default_factory=lambda: uuid4().hex)
    text: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    class Settings:
        name = "micro_posts"
        indexes = [
            IndexModel([("author_id", ASCENDING), ("created_at", DESCENDING)], name="posts_author_time"),
            IndexModel([("share_id", ASCENDING)], name="posts_share_id"),
        ]


class Article(Document):
    author_id: PydanticObjectId
    share_id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    summary: str = ""
    body: dict[str, Any]
    thumbnail_key: str | None = None
    status: Literal["draft", "scheduled", "published"] = "draft"
    created_at: datetime
    updated_at: datetime
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    deleted_at: datetime | None = None

    class Settings:
        name = "articles"
        indexes = [
            IndexModel([("author_id", ASCENDING), ("created_at", DESCENDING)], name="articles_author_time"),
            IndexModel([("status", ASCENDING), ("published_at", DESCENDING)], name="articles_public_feed"),
            IndexModel([("status", ASCENDING), ("scheduled_at", ASCENDING)], name="articles_scheduled_publish"),
            IndexModel([("share_id", ASCENDING)], name="articles_share_id"),
        ]
