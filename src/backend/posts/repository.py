"""Beanie queries owned by the feature."""

from typing import Any

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.posts.models import MicroPost
from backend.posts.visibility import visible_post_stages


class PostRepository:
    """Persistence queries for posts."""

    @staticmethod
    async def get_post(post_id: PydanticObjectId, session: AsyncClientSession | None = None) -> MicroPost | None:
        """Load a micro-post document by its identifier.

        :param post_id: MongoDB identifier of the micro-post.
        :param session: Optional MongoDB session for the operation or caller
            transaction.
        :return: The micro-post, or None when absent.
        """
        return await MicroPost.get(post_id, session=session)

    @staticmethod
    async def load_feed(
        conditions: dict[str, Any], limit: int, group_for_profile: PydanticObjectId | None = None,
    ) -> list[MicroPost]:
        """Load a bounded publication page with one continuation candidate.

        :param conditions: Visibility, author, and cursor filters supplied by the feed coordinator.
        :param limit: Page size before the extra continuation candidate.
        :param group_for_profile: Optional profile whose author-thread continuations are grouped before limiting.
        :return: Documents ordered by publication time and identifier descending.
        """
        rows = await MicroPost.aggregate([
            {"$match": conditions}, {"$sort": {"created_at": -1, "_id": -1}},
            *visible_post_stages(group_for_profile=group_for_profile), {"$limit": limit + 1},
        ]).to_list()
        return [MicroPost.model_validate(row) for row in rows]

    @staticmethod
    async def find_shared(owner_id: PydanticObjectId, share_id: str) -> MicroPost | None:
        """Find an undeleted post; the caller must enforce pending, archive, and discussion visibility.

        :param owner_id: Account owning the publication.
        :param share_id: Persisted stable share identity.
        :return: The post, possibly private, or None when absent or deleted.
        """
        return await MicroPost.find_one({"owner_id": owner_id, "share_id": share_id, "deleted_at": None})
