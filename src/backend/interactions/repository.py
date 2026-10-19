"""Beanie relationship queries and batched visible-publication hydration."""

from typing import Any, Literal

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.articles.models import Article
from backend.interactions.models import InteractionKind, PublicationInteraction
from backend.posts.models import MicroPost
from backend.publications.access import PublicationKind


class InteractionRepository:
    """Read unique interaction edges, public counts, and bounded relationship pages."""

    @staticmethod
    async def get(
        kind: PublicationKind, publication_id: PydanticObjectId, user_id: PydanticObjectId,
        action: InteractionKind, session: AsyncClientSession,
    ) -> PublicationInteraction | None:
        """Find an actor's unique edge within a transaction.

        :param kind: Containing publication type.
        :param publication_id: Original publication identifier.
        :param user_id: Acting account identifier.
        :param action: Interaction to find.
        :param session: Caller mutation session.
        :return: The matching edge, or None when the desired state is absent.
        """
        return await PublicationInteraction.find_one({
            "publication_kind": kind, "publication_id": publication_id, "user_id": user_id, "action": action,
        }, session=session)

    @staticmethod
    async def counts(kind: PublicationKind, publication_id: PydanticObjectId) -> dict[str, int]:
        """Aggregate public interaction counts without counting private saves.

        :param kind: Original publication type.
        :param publication_id: Original publication identifier.
        :return: Like and repost counts indexed by action.
        """
        rows = await PublicationInteraction.find({
            "publication_kind": kind, "publication_id": publication_id, "action": {"$in": ["like", "repost"]},
        }).aggregate([{"$group": {"_id": "$action", "count": {"$sum": 1}}}]).to_list()

        return {row["_id"]: row["count"] for row in rows}

    @staticmethod
    async def viewer_actions(
        kind: PublicationKind, publication_id: PydanticObjectId, user_id: PydanticObjectId | None,
    ) -> set[str]:
        """Read private interaction flags for only the current viewer.

        :param kind: Original publication type.
        :param publication_id: Original publication identifier.
        :param user_id: Current viewer identifier, or None for an anonymous reader.
        :return: The viewer's active actions, or an empty set when anonymous.
        """
        if user_id is None:
            return set()

        edges = await PublicationInteraction.find({
            "publication_kind": kind, "publication_id": publication_id, "user_id": user_id,
            "action": {"$in": ["like", "save", "repost"]},
        }).to_list()

        return {edge.action for edge in edges}

    @staticmethod
    async def page(
        user_id: PydanticObjectId, action: Literal["save", "repost"], cursor: PydanticObjectId | None, limit: int,
    ) -> list[PublicationInteraction]:
        """Read an account's saves or reposts in descending relationship-ID order.

        :param user_id: Account whose relationships are requested.
        :param action: Private saves or public reposts.
        :param cursor: Last scanned relationship ID, or None for the first page.
        :param limit: Bounded page size; one extra relationship detects continuation.
        :return: At most limit plus one relationships, including edges whose originals became unavailable.
        """
        conditions: dict[str, Any] = {"user_id": user_id, "action": action}

        if cursor is not None:
            conditions["_id"] = {"$lt": cursor}

        return await PublicationInteraction.find(conditions).sort(("_id", -1)).limit(limit + 1).to_list()

    @staticmethod
    async def originals(
        edges: list[PublicationInteraction],
    ) -> dict[tuple[PublicationKind, PydanticObjectId], MicroPost | Article]:
        """Load currently public originals in at most two bounded collection queries.

        :param edges: Bounded relationship page to hydrate.
        :return: Visible originals indexed by collection kind and original ID, preventing cross-collection collisions.
        """
        result: dict[tuple[PublicationKind, PydanticObjectId], MicroPost | Article] = {}

        for kind, model in (("micro_post", MicroPost), ("article", Article)):
            ids = [edge.publication_id for edge in edges if edge.publication_kind == kind]

            if not ids:
                continue

            conditions: dict[str, Any] = {"_id": {"$in": ids}, "deleted_at": None}

            if kind == "article":
                conditions["status"] = "published"
                conditions["published_at"] = {"$ne": None}

            result.update({(kind, item.id): item for item in await model.find(conditions).to_list()})

        return result
