"""Separate persistence shapes for threaded post replies and flat article comments."""

from datetime import datetime

from beanie import Document, PydanticObjectId
from pydantic import BaseModel
from pymongo import ASCENDING, IndexModel


class CommentContent(BaseModel):
    """Store plain-text discussion content and soft-deletion metadata."""

    author_id: PydanticObjectId
    text: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class PostReply(Document, CommentContent):
    """One immutable tree position in a post's discussion, retained as a tombstone on deletion."""

    post_id: PydanticObjectId
    parent_id: PydanticObjectId | None = None
    root_id: PydanticObjectId
    depth: int = 0
    reply_revision: int = 0

    class Settings:
        """Indexes for direct-child pages, thread references, and live reply counts."""

        name = "post_replies"
        indexes = [
            IndexModel(
                [("post_id", ASCENDING), ("parent_id", ASCENDING), ("_id", ASCENDING)],
                name="post_reply_children",
            ),
            IndexModel([("parent_id", ASCENDING)], name="post_reply_parent_count"),
            IndexModel([("post_id", ASCENDING), ("root_id", ASCENDING)], name="post_reply_thread"),
            IndexModel([("post_id", ASCENDING), ("deleted_at", ASCENDING)], name="post_reply_live_count"),
        ]


class ArticleComment(Document, CommentContent):
    """A flat article comment with no parent, thread, or reply relationship."""

    article_id: PydanticObjectId

    class Settings:
        """Indexes for flat comment pages and live comment counts."""

        name = "article_comments"
        indexes = [
            IndexModel([("article_id", ASCENDING), ("_id", ASCENDING)], name="article_comment_page"),
            IndexModel([("article_id", ASCENDING), ("deleted_at", ASCENDING)], name="article_comment_live_count"),
        ]
