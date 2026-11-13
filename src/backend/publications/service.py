"""Transactional owner archive and profile pin operations across publication types."""

from datetime import UTC, datetime
from typing import Literal

from beanie import PydanticObjectId

from backend.articles.models import Article
from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.core.errors import Conflict, InvalidOperation, NotFound
from backend.core.resources import AppResources
from backend.core.transactions import transaction
from backend.feeds.cache import invalidate_public_feed
from backend.feeds.cursors import FeedCursor
from backend.feeds.presenters import feed_item
from backend.feeds.schemas import ArticleFeedItem, PostFeedItem
from backend.posts.models import MicroPost
from backend.posts.threads import attach_thread_previews
from backend.posts.visibility import visible_post_stages
from backend.profiles.models import User
from backend.profiles.repository import ProfileRepository
from backend.publications.access import PublicationKind, object_id, public_publication
from backend.publications.schemas import ArchivePage
from backend.search.sync import sync_publication


class PublicationStateService:
    """Manage owner-only archives and a shared five-publication pin allowance."""

    def __init__(self, resources: AppResources, audit: AuditContext) -> None:
        """Configure publication state operations.

        :param resources: Application database and cache clients.
        :param audit: Request audit metadata for mutations.
        :return: None.
        """
        self.resources = resources
        self.audit = audit

    async def change(
        self, kind: PublicationKind, resource_id: str, action: Literal["archive", "pin"],
        enabled: bool, owner: User,
    ) -> MicroPost | Article:
        """Set one owner state in an audited transaction, preserving no-op timestamps.

        Updating a dedicated account revision serializes pin counts across both
        collections. Archive state does not change content timestamps or article
        publication state, and archiving clears the publication's pin. Search
        projections are updated in the same transaction when archive visibility changes.

        :param kind: Publication collection to mutate.
        :param resource_id: Owned publication identifier.
        :param action: Archive state or profile pin state to set.
        :param enabled: Desired presence of the selected state.
        :param owner: Authenticated publication owner; featured authors cannot mutate.
        :return: The committed publication with its current state timestamps.
        """
        model = MicroPost if kind == "micro_post" else Article
        async with transaction(self.resources.mongo) as session:
            account = await User.get(owner.id, session=session)
            if account is None:
                raise NotFound("Account not found")
            await account.update({"$inc": {"publication_state_revision": 1}}, session=session)
            item = await model.get(object_id(resource_id), session=session)
            if item is None or item.deleted_at is not None or item.owner_id != owner.id:
                raise NotFound("Publication not found")
            if isinstance(item, MicroPost) and item.pending:
                raise InvalidOperation("Publish this upload draft first")
            if enabled and isinstance(item, Article) and item.status != "published":
                raise InvalidOperation("Only published articles can be archived or pinned")
            field = "archived_at" if action == "archive" else "pinned_at"
            if (getattr(item, field) is not None) == enabled:
                return item
            if action == "pin" and enabled:
                if item.archived_at is not None:
                    raise InvalidOperation("Unarchive this publication before pinning it")
                await public_publication(kind, resource_id, session, touch=True)
                conditions = {"owner_id": owner.id, "deleted_at": None, "pinned_at": {"$ne": None}}
                count = await MicroPost.find(conditions, session=session).count()
                count += await Article.find(conditions, session=session).count()
                if count >= 5:
                    raise Conflict("You can pin up to 5 publications. Unpin one first.")
            now = datetime.now(UTC)
            changes = {field: now if enabled else None}
            if action == "archive" and enabled:
                changes["pinned_at"] = None
            await item.update({"$set": changes}, session=session)
            if action == "archive":
                await sync_publication(item, session)
            await record_audit(
                self.audit,
                f"PUBLICATION_{'ARCHIVED' if enabled else 'UNARCHIVED'}" if action == "archive"
                else f"PUBLICATION_{'PINNED' if enabled else 'UNPINNED'}",
                actor_id=owner.id, target_type=kind, target_id=resource_id,
                metadata={"at": now.isoformat()}, session=session,
            )
        await invalidate_public_feed(self.resources.redis)
        return item

    async def archive(self, owner: User, cursor_text: str | None, limit: int) -> ArchivePage:
        """Read a bounded mixed archive without exposing another account's content.

        :param owner: Authenticated owner of the requested archive.
        :param cursor_text: Previous archive cursor, or None for the initial page.
        :param limit: Bounded number of cards to return.
        :return: Archive cards sorted by archive time, kind, and ID descending.
        """
        cursor = FeedCursor.decode(cursor_text)
        if cursor is not None and cursor.kind not in {"article", "micro_post"}:
            raise InvalidOperation("Invalid archive cursor")
        rows: list[tuple[datetime, PublicationKind, MicroPost | Article]] = []
        for kind, model in (("micro_post", MicroPost), ("article", Article)):
            conditions = {"owner_id": owner.id, "deleted_at": None, "archived_at": {"$ne": None}}
            if cursor is not None:
                conditions = {"$and": [conditions, cursor.conditions(kind, "archived_at")]}
            items = await model.find(conditions).sort(("archived_at", -1), ("_id", -1)).limit(limit + 1).to_list()
            rows.extend((item.archived_at, kind, item) for item in items)
        rows.sort(key=lambda row: (row[0], row[1], str(row[2].id)), reverse=True)
        page = rows[:limit]
        cards = await self._cards([item for _, _, item in page])
        next_cursor = None
        if len(rows) > limit:
            date, kind, item = page[-1]
            next_cursor = FeedCursor(date, kind, item.id).encode()
        return ArchivePage(items=cards, next_cursor=next_cursor)

    async def pins(self, owner_id: PydanticObjectId) -> list[PostFeedItem | ArticleFeedItem]:
        """Read currently public pins for a profile without exposing hidden originals.

        :param owner_id: Profile owner whose public pins are requested.
        :return: At most five cards ordered by pin time, kind, and ID descending.
        """
        conditions = {"owner_id": owner_id, "deleted_at": None, "pinned_at": {"$ne": None}}
        rows = await MicroPost.aggregate([
            {"$match": conditions}, *visible_post_stages(), {"$sort": {"pinned_at": -1, "_id": -1}}, {"$limit": 5},
        ]).to_list()
        posts = [MicroPost.model_validate(row) for row in rows]
        articles = await Article.find({
            **conditions, "archived_at": None, "status": "published", "published_at": {"$ne": None},
        }).sort(("pinned_at", -1), ("_id", -1)).limit(5).to_list()
        items = sorted(
            [*posts, *articles],
            key=lambda item: (item.pinned_at, "micro_post" if isinstance(item, MicroPost) else "article", str(item.id)),
            reverse=True,
        )[:5]
        cards = await self._cards(items)
        await attach_thread_previews(
            [card for card in cards if card.kind == "micro_post" and card.reply is None],
            [item for item in items if isinstance(item, MicroPost) and item.reply is None],
        )
        return cards

    async def _cards(self, publications: list[MicroPost | Article]) -> list[PostFeedItem | ArticleFeedItem]:
        """Present a bounded publication page using one batched author query.

        :param publications: Already authorized publications in response order.
        :return: Typed cards preserving the owner-first author order.
        """
        ids = list({author_id for item in publications for author_id in item.author_ids})
        authors = {user.id: user for user in await ProfileRepository.users_by_ids(ids)} if ids else {}
        if any(author_id not in authors for item in publications for author_id in item.author_ids):
            raise NotFound("Author not found")
        return [feed_item(item, [authors[author_id] for author_id in item.author_ids]) for item in publications]
