"""Bounded Beanie discussion queries with separate flat and threaded policies."""

from typing import Any

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.comments.models import ArticleComment, PostReply
from backend.publications.access import PublicationKind

type Discussion = PostReply | ArticleComment


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
        model = PostReply if kind == "micro_post" else ArticleComment
        field = "post_id" if kind == "micro_post" else "article_id"

        return await model.find_one({"_id": comment_id, field: publication_id}, session=session)

    @staticmethod
    async def page(
        kind: PublicationKind,
        publication_id: PydanticObjectId,
        parent_id: PydanticObjectId | None,
        cursor: PydanticObjectId | None,
        limit: int,
    ) -> list[Discussion]:
        """Read a bounded flat page or one direct-child level, retaining tombstones.

        :param kind: Discussion model selected by the publication type.
        :param publication_id: Containing post or article identifier.
        :param parent_id: Parent reply for a post level; None selects roots and is ignored for articles.
        :param cursor: Last comment ObjectId from the previous oldest-first page.
        :param limit: Requested page size; one additional row is read to detect continuation.
        :return: At most limit plus one scoped comments in ObjectId order.
        """
        model = PostReply if kind == "micro_post" else ArticleComment
        field = "post_id" if kind == "micro_post" else "article_id"
        conditions: dict[str, Any] = {field: publication_id}

        if kind == "micro_post":
            conditions["parent_id"] = parent_id

        if cursor is not None:
            conditions["_id"] = {"$gt": cursor}

        return await model.find(conditions).sort(("_id", 1)).limit(limit + 1).to_list()

    @staticmethod
    async def child_counts(reply_ids: list[PydanticObjectId]) -> dict[PydanticObjectId, int]:
        """Count direct children for a page in one aggregation.

        :param reply_ids: Bounded page of parent reply identifiers.
        :return: Counts indexed by parent ID, including deleted children to retain thread navigation.
        """
        if not reply_ids:
            return {}

        rows = await PostReply.find({"parent_id": {"$in": reply_ids}}).aggregate(
            [{"$group": {"_id": "$parent_id", "count": {"$sum": 1}}}]
        ).to_list()

        return {row["_id"]: row["count"] for row in rows}

    @staticmethod
    async def live_count(kind: PublicationKind, publication_id: PydanticObjectId) -> int:
        """Count nondeleted discussion entries across all post levels or one flat article.

        :param kind: Publication type selecting the discussion collection.
        :param publication_id: Containing publication identifier.
        :return: Number of live comments or replies.
        """
        model = PostReply if kind == "micro_post" else ArticleComment
        field = "post_id" if kind == "micro_post" else "article_id"

        return await model.find({field: publication_id, "deleted_at": None}).count()
