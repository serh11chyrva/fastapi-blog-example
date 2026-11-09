"""Separate persistence shapes for threaded post replies and flat article comments."""

from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel
from pymongo import ASCENDING, DESCENDING, IndexModel


class CommentContent(BaseModel):
    """Store plain-text discussion content and soft-deletion metadata."""

    author_id: PydanticObjectId
    text: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    likes_count: int = 0


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
            IndexModel(
                [("post_id", ASCENDING), ("parent_id", ASCENDING), ("deleted_at", ASCENDING),
                 ("likes_count", DESCENDING), ("_id", DESCENDING)],
                name="post_reply_rank",
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
            IndexModel(
                [("author_id", ASCENDING), ("deleted_at", ASCENDING), ("created_at", DESCENDING), ("_id", DESCENDING)],
                name="article_comment_profile_timeline",
            ),
            IndexModel(
                [("article_id", ASCENDING), ("deleted_at", ASCENDING), ("likes_count", DESCENDING), ("_id", DESCENDING)],
                name="article_comment_rank",
            ),
            IndexModel([("article_id", ASCENDING), ("deleted_at", ASCENDING)], name="article_comment_live_count"),
        ]


class CommentLike(Document):
    """One account's reaction to a scoped comment or reply."""

    kind: Literal["article", "micro_post"]
    comment_id: PydanticObjectId
    user_id: PydanticObjectId

    class Settings:
        """Indexes for unique reactions and batched viewer state."""

        name = "comment_likes"
        indexes = [
            IndexModel(
                [("kind", ASCENDING), ("comment_id", ASCENDING), ("user_id", ASCENDING)],
                unique=True,
                name="comment_like_unique",
            ),
        ]
