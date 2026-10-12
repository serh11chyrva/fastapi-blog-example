from datetime import datetime
from typing import Any, Literal

from beanie import Document, PydanticObjectId
from pymongo import ASCENDING, DESCENDING, IndexModel


class MicroPost(Document):
    author_id: PydanticObjectId
    text: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    class Settings:
        name = "micro_posts"
        indexes = [IndexModel([("author_id", ASCENDING), ("created_at", DESCENDING)], name="posts_author_time")]


class Article(Document):
    author_id: PydanticObjectId
    title: str
    summary: str = ""
    body: dict[str, Any]
    status: Literal["draft", "published"] = "draft"
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    deleted_at: datetime | None = None

    class Settings:
        name = "articles"
        indexes = [
            IndexModel([("author_id", ASCENDING), ("created_at", DESCENDING)], name="articles_author_time"),
            IndexModel([("status", ASCENDING), ("published_at", DESCENDING)], name="articles_public_feed"),
        ]
