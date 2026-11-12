"""Bounded Beanie queries over publication-backed discussion trees."""

from typing import Any, Literal

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.comments.conversion import ReplyMapping
from backend.posts.models import MicroPost
from backend.posts.visibility import visible_post_stages
from backend.publications.access import PublicationKind

type Discussion = MicroPost
type DiscussionSort = Literal["oldest", "newest", "most_liked"]


class CommentRepository:
    """Read scoped comments, paginated levels, and direct-child counts."""

    @staticmethod
    async def get(
        kind: PublicationKind,
        publication_id: PydanticObjectId,
        comment_id: PydanticObjectId,
        session: AsyncClientSession | None = None,
    ) -> Discussion | None:
        """Read a comment only within its containing publication.

        :param kind: Discussion model selected by the publication type.
        :param publication_id: Containing post or article identifier.
        :param comment_id: Comment or reply identifier to load.
        :param session: Optional caller transaction session.
        :return: The scoped comment, or None if it does not belong to this publication.
        """
        publication = await MicroPost.get(publication_id, session=session) if kind == "micro_post" else None
        context = publication.reply if publication is not None else None
        conditions = {
            "reply.kind": context.kind if context else kind,
            "reply.publication_id": context.publication_id if context else publication_id,
        }
        source = "post_replies" if kind == "micro_post" else "article_comments"
        mapping = await ReplyMapping.get(f"{source}:{comment_id}", session=session)
        resolved = mapping.post_id if mapping else comment_id
        return await MicroPost.find_one({"_id": resolved, **conditions}, session=session)

    @staticmethod
    async def page(
        kind: PublicationKind,
        publication_id: PydanticObjectId,
        parent_id: PydanticObjectId | None,
        cursor: PydanticObjectId | None,
        limit: int,
        sort: DiscussionSort = "oldest",
        likes_count: int | None = None,
        viewer_id: PydanticObjectId | None = None,
    ) -> list[Discussion]:
        """Read one bounded discussion level, retaining tombstones in oldest order.

        :param kind: Discussion model selected by the publication type.
        :param publication_id: Containing post or article identifier.
        :param parent_id: Parent reply for either discussion type; None selects roots or reply-publication children.
        :param cursor: Last comment ObjectId from the preceding page.
        :param limit: Requested page size; one additional row is read to detect continuation.
        :param sort: Legacy oldest order or a live-only newest or ranked order.
        :param likes_count: Last seen rank when continuing a most-liked page.
        :param viewer_id: Optional owner for reading its own archived discussion.
        :return: At most limit plus one scoped entries in the requested order.
        """
        publication = await MicroPost.get(publication_id) if kind == "micro_post" else None
        context = publication.reply if publication is not None else None
        if parent_id is not None:
            parent = await CommentRepository.get(kind, publication_id, parent_id)
            parent_id = parent.id if parent else parent_id
        conditions: dict[str, Any] = {
            "reply.kind": context.kind if context else kind,
            "reply.publication_id": context.publication_id if context else publication_id,
            "reply.parent_id": parent_id if parent_id is not None else publication_id if context else None,
        }

        order = [("_id", 1 if sort == "oldest" else -1)]
        if sort != "oldest":
            conditions["deleted_at"] = None
        if sort == "most_liked":
            order.insert(0, ("likes_count", -1))
            if cursor is not None:
                conditions["$or"] = [
                    {"likes_count": {"$lt": likes_count}},
                    {"likes_count": likes_count, "_id": {"$lt": cursor}},
                ]
        elif cursor is not None:
            conditions["_id"] = {"$gt" if sort == "oldest" else "$lt": cursor}

        rows = await MicroPost.aggregate([
            {"$match": conditions}, *visible_post_stages(viewer_id=viewer_id),
            {"$sort": dict(order)}, {"$limit": limit + 1},
        ]).to_list()
        return [MicroPost.model_validate(row) for row in rows]

    @staticmethod
    async def child_counts(
        reply_ids: list[PydanticObjectId], viewer_id: PydanticObjectId | None = None,
    ) -> dict[PydanticObjectId, int]:
        """Count direct children for a page in one aggregation.

        :param reply_ids: Bounded page of parent reply identifiers.
        :param viewer_id: Optional account permitted to see its own archived branches.
        :return: Visible child counts by parent ID, retaining deleted children but excluding inaccessible archives.
        """
        if not reply_ids:
            return {}

        rows = await MicroPost.aggregate([
            {"$match": {"reply.parent_id": {"$in": reply_ids}}},
            *visible_post_stages(viewer_id=viewer_id),
            {"$group": {"_id": "$reply.parent_id", "count": {"$sum": 1}}},
        ]).to_list()

        return {row["_id"]: row["count"] for row in rows}

    @staticmethod
    async def live_count(kind: PublicationKind, publication_id: PydanticObjectId) -> int:
        """Count live entries across an original discussion or direct children of a reply.

        :param kind: Publication type selecting the discussion collection.
        :param publication_id: Containing publication identifier.
        :return: Number of live comments or replies.
        """
        publication = await MicroPost.get(publication_id) if kind == "micro_post" else None
        conditions = {"reply.kind": kind, "reply.publication_id": publication_id, "deleted_at": None}
        if publication is not None and publication.reply is not None:
            conditions = {"reply.parent_id": publication_id, "deleted_at": None}
        rows = await MicroPost.aggregate([
            {"$match": conditions}, *visible_post_stages(), {"$count": "count"},
        ]).to_list()
        return rows[0]["count"] if rows else 0
