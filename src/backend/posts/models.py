from datetime import datetime
from typing import Literal
from uuid import uuid4

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from backend.publications.attachments import PublicationAttachments
from backend.publications.models import PublicationAuthors


class ReplyMetadata(BaseModel):
    """Immutable original-publication reference and position in its discussion tree."""

    kind: Literal["article", "micro_post"]
    publication_id: PydanticObjectId
    parent_id: PydanticObjectId | None = None
    root_id: PydanticObjectId
    depth: int = Field(default=0, ge=0)


class MicroPost(Document, PublicationAuthors):
    """Short-form publication with ordered authors, owner-only archive state, and profile pins."""

    attachments: PublicationAttachments = Field(default_factory=list)
    reply: ReplyMetadata | None = None
    legacy_source: str | None = None
    likes_count: int = 0
    reply_revision: int = 0
    pending: bool = False
    draft_key: str | None = None
    interaction_revision: int = 0
    share_id: str = Field(default_factory=lambda: uuid4().hex)
    text: str
    image_keys: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    archived_at: datetime | None = None
    pinned_at: datetime | None = None

    class Settings:
        """Beanie collection and index configuration for MicroPost."""

        name = "micro_posts"
        indexes = [
            IndexModel(
                [("owner_id", ASCENDING), ("archived_at", DESCENDING), ("_id", DESCENDING)],
                name="posts_owner_archive",
            ),
            IndexModel([("owner_id", ASCENDING), ("pinned_at", DESCENDING)], name="posts_owner_pins"),
            IndexModel(
                [("draft_key", ASCENDING)], unique=True,
                partialFilterExpression={"draft_key": {"$type": "string"}}, name="post_draft_key",
            ),
            IndexModel([("pending", ASCENDING), ("updated_at", ASCENDING)], name="post_pending_expiry"),
            IndexModel(
                [("legacy_source", ASCENDING)], unique=True,
                partialFilterExpression={"legacy_source": {"$type": "string"}}, name="post_legacy_source",
            ),
            IndexModel(
                [("reply.kind", ASCENDING), ("reply.publication_id", ASCENDING),
                 ("reply.parent_id", ASCENDING), ("_id", ASCENDING)], name="post_discussion_children",
            ),
            IndexModel(
                [("reply.publication_id", ASCENDING), ("reply.parent_id", ASCENDING),
                 ("deleted_at", ASCENDING), ("likes_count", DESCENDING), ("_id", DESCENDING)],
                name="post_discussion_rank",
            ),
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
