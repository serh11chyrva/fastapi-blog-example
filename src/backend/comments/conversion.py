"""Resumable conversion of legacy discussions into publication-backed replies."""

from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import Field
from redis.asyncio import Redis

from backend.comments.models import ArticleComment, CommentLike, PostReply
from backend.interactions.models import PublicationInteraction
from backend.posts.models import MicroPost, ReplyMetadata


class ReplyMapping(Document):
    """Persist legacy identities and per-record conversion checkpoints for safe retries."""

    id: str
    post_id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    complete: bool = False

    class Settings:
        """Keep migration checkpoints separate from publication content."""

        name = "reply_migration_mappings"


async def mapped_id(source: str, legacy_id: PydanticObjectId) -> PydanticObjectId:
    """Resolve a preallocated legacy identity, rejecting incomplete migration preparation.

    :param source: Legacy collection name.
    :param legacy_id: Identifier of the legacy record.
    :return: Allocated publication identity.
    """
    mapping = await ReplyMapping.get(f"{source}:{legacy_id}")
    if mapping is None:
        raise ValueError(f"Missing reply mapping for {source}:{legacy_id}")

    return mapping.post_id


async def require_discussion_migration() -> None:
    """Refuse new-storage API startup when legacy discussion conversion is unfinished.

    This rollout guard compares retained source counts with completed checkpoints;
    it does not replace the operator's full pre-deployment reconciliation.

    :return: None; incomplete conversion raises RuntimeError before the API accepts writes.
    """
    for source, model in (("post_replies", PostReply), ("article_comments", ArticleComment)):
        expected = await model.find_all().count()
        completed = await ReplyMapping.find({"_id": {"$regex": f"^{source}:"}, "complete": True}).count()
        if completed < expected:
            raise RuntimeError("Legacy discussions need conversion; run python -m backend.migrate discussions "
                               "with API writes paused before starting this version")


async def migrate_discussions(redis: Redis, report: bool = False) -> dict[str, int]:
    """Copy legacy discussions and likes once while retaining source collections.

    Run with application writes paused. Checkpoints are marked only after each post
    and its likes have been copied. A process crash leaves a Redis lock that the
    operator must explicitly release after confirming no migration is running.

    :param redis: Redis client providing the exclusive conversion lock.
    :param report: Report source and completed counts without converting records.
    :return: Legacy record and completed mapping counts.
    """
    counts = {
        "post_replies": await PostReply.find_all().count(),
        "article_comments": await ArticleComment.find_all().count(),
        "completed": await ReplyMapping.find({"complete": True}).count(),
    }
    if report:
        return counts

    async with redis.lock("migration:discussion-posts:v1", timeout=None, blocking_timeout=1):
        for source, model in (("post_replies", PostReply), ("article_comments", ArticleComment)):
            async for item in model.find_all().sort("_id"):
                key = f"{source}:{item.id}"
                if await ReplyMapping.get(key) is None:
                    collision = await MicroPost.get(item.id)
                    allocated = await ReplyMapping.find_one({"post_id": item.id})
                    await ReplyMapping(
                        id=key, post_id=item.id if collision is None and allocated is None else PydanticObjectId(),
                    ).insert()

        for source, model in (("post_replies", PostReply), ("article_comments", ArticleComment)):
            async for item in model.find_all().sort("_id"):
                mapping = await ReplyMapping.get(f"{source}:{item.id}")
                if mapping.complete:
                    continue
                kind = "micro_post" if source == "post_replies" else "article"
                context = ReplyMetadata(
                    kind=kind,
                    publication_id=item.post_id if isinstance(item, PostReply) else item.article_id,
                    parent_id=(
                        await mapped_id(source, item.parent_id)
                        if isinstance(item, PostReply) and item.parent_id is not None else None
                    ),
                    root_id=await mapped_id(source, item.root_id) if isinstance(item, PostReply) else mapping.post_id,
                    depth=item.depth if isinstance(item, PostReply) else 0,
                )
                post = await MicroPost.get(mapping.post_id)
                if post is None:
                    post = MicroPost(
                        id=mapping.post_id, owner_id=item.author_id, text=item.text[:280], reply=context,
                        legacy_source=mapping.id, created_at=item.created_at, updated_at=item.updated_at,
                        deleted_at=item.deleted_at, share_id=f"30000000{mapping.post_id}",
                    )
                    await post.insert()
                if post.legacy_source != mapping.id:
                    raise ValueError(f"Migration identity collision: {mapping.id}")

                async for like in CommentLike.find({"kind": kind, "comment_id": item.id}):
                    query = {
                        "publication_kind": "micro_post", "publication_id": post.id,
                        "user_id": like.user_id, "action": "like",
                    }
                    if await PublicationInteraction.find_one(query) is None:
                        await PublicationInteraction(
                            **query, created_at=like.id.generation_time or datetime.now(UTC),
                        ).insert()
                post.likes_count = await PublicationInteraction.find({
                    "publication_kind": "micro_post", "publication_id": post.id, "action": "like",
                }).count()
                await post.save()
                mapping.complete = True
                await mapping.save()

    counts["completed"] = await ReplyMapping.find({"complete": True}).count()
    return counts
