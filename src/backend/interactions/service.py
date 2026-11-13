"""Audited idempotent interaction state and private/public relationship lists."""

from datetime import UTC, datetime
from typing import Literal, cast

from pymongo.errors import DuplicateKeyError

from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.comments.repository import CommentRepository
from backend.core.errors import Conflict, InvalidOperation, NotFound
from backend.core.resources import AppResources
from backend.core.transactions import transaction
from backend.feeds.cache import invalidate_public_feed
from backend.feeds.presenters import feed_item, repost_item
from backend.feeds.schemas import ArticleFeedItem, PostFeedItem, RepostPage
from backend.interactions.models import InteractionKind, PublicationInteraction
from backend.interactions.repository import InteractionRepository
from backend.interactions.schemas import InteractionSummary, SavedPage, SavedPublication
from backend.notifications.models import NotificationTarget
from backend.notifications.service import NotificationService
from backend.posts.models import MicroPost
from backend.profiles.models import User
from backend.profiles.repository import ProfileRepository
from backend.publications.access import PublicationKind, object_id, public_publication


class InteractionService:
    """Manage unique likes, private saves, and unquoted public post reposts."""

    def __init__(self, resources: AppResources, audit: AuditContext) -> None:
        """Initialize interaction operations with infrastructure and audit context.

        :param resources: Application-owned MongoDB and Redis clients.
        :param audit: Request metadata attached to transactional audit events.
        :return: None.
        """
        self.resources = resources
        self.audit = audit
        self.repository = InteractionRepository()

    async def set_state(
        self,
        kind: PublicationKind,
        publication_id: str,
        action: InteractionKind,
        enabled: bool,
        owner: User,
    ) -> None:
        """Set an interaction state once, committing the edge, audit, and notification changes together.

        Creation requires a public original and writes a visibility guard on it. Removal is also
        allowed after deletion or unpublishing, so accounts can clear inaccessible saved content.
        Repeated desired states are no-ops. Concurrent requests may receive 409 and must reload.
        Likes and reposts notify the object's owner except for self-actions; undoing
        either action retracts its source event. Private saves never create notifications.

        :param kind: Original publication type.
        :param publication_id: Original publication identifier.
        :param action: Like, save, or post-only repost.
        :param enabled: True to create the edge; False to remove it.
        :param owner: Authenticated account whose state is changed.
        :return: None.
        """
        if action == "repost" and kind != "micro_post":
            raise InvalidOperation("Only micro-posts can be reposted")

        resource_id = object_id(publication_id)
        changed = False

        try:
            async with transaction(self.resources.mongo) as session:
                if enabled:
                    publication = await public_publication(kind, publication_id, session, touch=True)

                edge = await self.repository.get(kind, resource_id, owner.id, action, session)

                if enabled and edge is None:
                    edge = PublicationInteraction(
                        publication_kind=kind,
                        publication_id=resource_id,
                        user_id=owner.id,
                        action=action,
                        created_at=datetime.now(UTC),
                    )
                    await edge.insert(session=session)
                    changed = True
                elif not enabled and edge is not None:
                    await edge.delete(session=session)
                    changed = True

                if changed and action == "like" and kind == "micro_post":
                    await MicroPost.find({"_id": resource_id, "reply": {"$ne": None}}, session=session).update_many(
                        {"$inc": {"likes_count": 1 if enabled else -1}},
                    )

                if changed:
                    if action in {"like", "repost"}:
                        notifications = NotificationService(self.resources)
                        if enabled:
                            await notifications.emit(
                                recipient_id=publication.owner_id, actor_id=owner.id, kind=action,
                                source_kind="interaction", source_id=edge.id, occurred_at=edge.created_at,
                                target=NotificationTarget(kind=kind, id=resource_id), session=session,
                            )
                        else:
                            await notifications.retract("interaction", edge.id, session)
                    await record_audit(
                        self.audit,
                        f"PUBLICATION_{action.upper()}_{'ADDED' if enabled else 'REMOVED'}",
                        actor_id=owner.id,
                        target_type=kind,
                        target_id=publication_id,
                        session=session,
                    )
        except DuplicateKeyError as exc:
            raise Conflict("Interaction changed; reload before retrying") from exc

        if changed and action == "repost":
            await invalidate_public_feed(self.resources.redis)

    async def summary(
        self,
        kind: PublicationKind,
        publication_id: str,
        viewer: User | None,
    ) -> InteractionSummary:
        """Read uncached public counts plus private state for the current viewer.

        :param kind: Public publication type.
        :param publication_id: Public publication identifier.
        :param viewer: Current account, or None for anonymous false flags.
        :return: Live counts and viewer flags; article repost fields are null and save totals are never exposed.
        """
        publication = await public_publication(kind, publication_id)
        counts = await self.repository.counts(kind, publication.id)
        actions = await self.repository.viewer_actions(kind, publication.id, viewer.id if viewer else None)

        return InteractionSummary(
            likes_count=counts.get("like", 0),
            comments_count=await CommentRepository.live_count(kind, publication.id),
            reposts_count=counts.get("repost", 0) if kind == "micro_post" else None,
            liked="like" in actions,
            saved="save" in actions,
            reposted="repost" in actions if kind == "micro_post" else None,
        )

    async def list_entries(
        self,
        user: User,
        action: Literal["save", "repost"],
        cursor: str | None,
        limit: int,
    ) -> SavedPage | RepostPage:
        """Hydrate a bounded relationship page while filtering unavailable originals.

        :param user: Account owning private saves or public reposts; callers enforce save-list ownership.
        :param action: List private saves or public reposts.
        :param cursor: Last scanned relationship ID from a previous page.
        :param limit: Bounded number of relationship records to scan, not a promise of visible item count.
        :return: A typed page; empty pages can have a next cursor when hidden originals were scanned.
        """
        rows = await self.repository.page(user.id, action, object_id(cursor) if cursor else None, limit)
        edges = rows[:limit]
        originals = await self.repository.originals(edges)
        authors = await ProfileRepository.users_by_ids(
            list({author_id for original in originals.values() for author_id in original.author_ids})
        )
        by_id = {author.id: author for author in authors}
        items = []

        for edge in edges:
            original = originals.get((edge.publication_kind, edge.publication_id))

            if original is None or any(author_id not in by_id for author_id in original.author_ids):
                continue

            cards = [by_id[author_id] for author_id in original.author_ids]

            if action == "save":
                items.append(
                    SavedPublication(
                        id=str(edge.id),
                        saved_at=edge.created_at,
                        publication=cast(PostFeedItem | ArticleFeedItem, feed_item(original, cards)),
                    )
                )
            elif isinstance(original, MicroPost):
                items.append(repost_item(original, cards, edge, user))

        values = dict(items=items, next_cursor=str(edges[-1].id) if len(rows) > limit else None)

        return SavedPage(**values) if action == "save" else RepostPage(**values)

    async def profile_reposts(self, username: str, cursor: str | None, limit: int) -> RepostPage:
        """Read an account's public repost history by handle.

        :param username: Public handle, optionally prefixed with @.
        :param cursor: Last scanned repost relationship identifier.
        :param limit: Bounded relationship page size.
        :return: Visible original posts wrapped with their reposter and repost timestamp.
        """
        user = await ProfileRepository.find_by_username(username)

        if user is None:
            raise NotFound("Profile not found")

        page = await self.list_entries(user, "repost", cursor, limit)

        return cast(RepostPage, page)
