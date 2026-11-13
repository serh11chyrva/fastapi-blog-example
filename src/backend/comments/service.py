"""Audited comment mutations and visibility-aware discussion reads."""

from datetime import UTC, datetime

from beanie import PydanticObjectId

from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.comments.presenters import comment_responses
from backend.comments.repository import CommentRepository, Discussion, DiscussionSort
from backend.comments.schemas import ArticleCommentPage, CommentText, PostReplyPage
from backend.core.config import get_settings
from backend.core.errors import InvalidOperation, NotFound
from backend.core.resources import AppResources
from backend.core.transactions import transaction
from backend.feeds.cache import invalidate_public_feed
from backend.links.cache import enqueue_attachments
from backend.posts.content import retained_image_keys, validate_post_content
from backend.posts.models import MicroPost, ReplyMetadata
from backend.posts.service import PostService
from backend.posts.visibility import visible_post_stages
from backend.profiles.models import User
from backend.publications.access import (
    PublicationKind, object_id, public_publication, readable_discussion, writable_discussion,
)
from backend.publications.attachment_validation import validate_attachment_references
from backend.search.sync import sync_publication
from backend.storage.cleanup import queue_deletion
from backend.storage.urls import publication_image_url


class CommentService:
    """Own publication-backed discussion trees with bounded incremental reads."""

    def __init__(self, resources: AppResources, audit: AuditContext) -> None:
        """Initialize discussion operations with infrastructure and request audit context.

        :param resources: Application-owned database and other infrastructure clients.
        :param audit: Request metadata for transactional audit events.
        :return: None.
        """
        self.resources = resources
        self.audit = audit
        self.repository = CommentRepository()

    async def create(
        self,
        kind: PublicationKind,
        publication_id: str,
        payload: CommentText,
        owner: User,
        parent_id: str | None = None,
    ) -> Discussion:
        """Create and index a reply with its audit event, guarding discussion availability in one transaction.

        Disabled article discussions reject new comments with 403 even when replying
        through a descendant post. Guard writes conflict with concurrent setting changes.

        :param kind: Containing publication type.
        :param publication_id: Public post or article identifier.
        :param payload: Validated text, attachment choice, and optional owned upload draft.
        :param owner: Authenticated account authoring the comment.
        :param parent_id: Optional undeleted parent in the same original discussion.
        :return: The persisted reply post with its immutable tree position.
        """
        async with transaction(self.resources.mongo) as session:
            publication = await writable_discussion(kind, publication_id, session)
            now = datetime.now(UTC)
            draft = None
            if payload.image_draft_id:
                draft = await PostService(self.resources, self.audit).owned(payload.image_draft_id, owner, session)
            reply_id = draft.id if draft else PydanticObjectId()
            parent = None
            original = publication.reply if isinstance(publication, MicroPost) else None
            if parent_id is not None:
                parent = await self.repository.get(kind, publication.id, object_id(parent_id), session)
                if parent is None or parent.deleted_at is not None:
                    raise NotFound("Parent reply not found")
                await public_publication("micro_post", str(parent.id), session, touch=True)
            elif original is not None:
                parent = publication
            context_kind = original.kind if original else kind
            context_id = original.publication_id if original else publication.id
            if draft is not None and not draft.pending:
                if (draft.reply is not None and draft.reply.kind == context_kind
                        and draft.reply.publication_id == context_id
                        and draft.reply.parent_id == (parent.id if parent else None)):
                    return draft
                raise InvalidOperation("Choose a private upload draft for this discussion")
            if parent is not None:
                await parent.update({"$inc": {"reply_revision": 1}}, session=session)
            comment = MicroPost(
                id=reply_id, owner_id=owner.id, text=payload.text, created_at=now, updated_at=now,
                attachments=payload.attachments,
                image_keys=retained_image_keys(draft.image_keys if draft else [], payload.retain_image_urls),
                draft_key=draft.draft_key if draft else None,
                reply=ReplyMetadata(
                    kind=context_kind,
                    publication_id=context_id,
                    parent_id=parent.id if parent else None,
                    root_id=parent.reply.root_id if parent else reply_id,
                    depth=parent.reply.depth + 1 if parent else 0,
                ),
            )

            validate_post_content(comment.text, comment.attachments, comment.image_keys)
            await validate_attachment_references(
                comment.attachments, [publication_image_url(key, "post-images") for key in comment.image_keys], session,
            )
            if draft:
                await comment.replace(session=session)
                for key in set(draft.image_keys) - set(comment.image_keys):
                    await queue_deletion(get_settings().publication_bucket, key, session=session)
            else:
                await comment.insert(session=session)
            await sync_publication(comment, session)
            await record_audit(
                self.audit,
                "COMMENT_CREATED",
                actor_id=owner.id,
                target_type="post_reply" if kind == "micro_post" else "article_comment",
                target_id=str(comment.id),
                metadata={"publication_id": publication_id},
                session=session,
            )

        await invalidate_public_feed(self.resources.redis)
        await enqueue_attachments(self.resources.redis, comment.attachments)
        return comment

    async def change(
        self,
        kind: PublicationKind,
        publication_id: str,
        comment_id: str,
        owner: User,
        payload: CommentText | None,
    ) -> Discussion:
        """Edit owned live text or erase an owned comment while retaining its tree position.

        :param kind: Containing publication type.
        :param publication_id: Public containing publication identifier.
        :param comment_id: Scoped comment or reply identifier.
        :param owner: Authenticated account; only the comment author may edit or delete.
        :param payload: Replacement text, or None to soft-delete; repeated deletion is idempotent.
        :return: The changed discussion entry, committed with its audit event.
        """
        item = await self.get(kind, publication_id, comment_id, owner.id)
        service = PostService(self.resources, self.audit)
        if item.owner_id != owner.id:
            raise NotFound("Comment not found")
        if payload is None:
            if item.deleted_at is None:
                await service.delete(str(item.id), owner)
            return await MicroPost.get(item.id)
        return await service.edit_post(str(item.id), payload, owner)

    async def set_like(
        self, kind: PublicationKind, publication_id: str, comment_id: str, owner: User, enabled: bool,
    ) -> None:
        """Change a live entry's viewer reaction and count in one transaction.

        :param kind: Type of containing publication.
        :param publication_id: Public containing publication identifier.
        :param comment_id: Live entry scoped to the publication.
        :param owner: Authenticated viewer changing their own reaction.
        :param enabled: Desired presence of the reaction.
        :return: None.
        """
        from backend.interactions.service import InteractionService

        item = await self.get(kind, publication_id, comment_id, owner.id)
        await InteractionService(self.resources, self.audit).set_state(
            "micro_post", str(item.id), "like", enabled, owner,
        )

    async def page(
        self,
        kind: PublicationKind,
        publication_id: str,
        parent_id: str | None,
        cursor: str | None,
        limit: int,
        viewer_id: PydanticObjectId | None = None,
        sort: DiscussionSort = "oldest",
    ) -> PostReplyPage | ArticleCommentPage:
        """Read one discussion level, rejecting disabled article discussions for every viewer.

        :param kind: Containing publication type.
        :param publication_id: Public containing publication identifier.
        :param parent_id: Optional parent reply; omission selects roots or children of a reply publication.
        :param cursor: Position from the same sort, or None for the first page.
        :param limit: Bounded page size supplied by the HTTP adapter.
        :param viewer_id: Current viewer for reaction flags and owned archive access, or None for anonymous reads.
        :param sort: Discussion order; post ranking applies to live roots only.
        :return: Typed discussion page with a continuation cursor when another row exists.
        """
        publication = await readable_discussion(kind, publication_id, viewer_id)
        parent = object_id(parent_id) if parent_id is not None else None

        if parent is not None:
            parent_item = await self.get(kind, publication_id, str(parent), viewer_id)
            parent = parent_item.id

        if kind == "micro_post" and sort != "oldest" and (parent is not None or sort != "most_liked"):
            raise InvalidOperation("Only root replies can be ranked")

        last_id = None
        last_count = None
        if cursor:
            if sort == "oldest":
                last_id = object_id(cursor)
            else:
                fields = cursor.split(".")
                if len(fields) != 3 or fields[0] != sort or not fields[1].isascii() or not fields[1].isdecimal():
                    raise InvalidOperation("Invalid discussion cursor for this sort")

                last_count = int(fields[1])
                if last_count > 2**63 - 1:
                    raise InvalidOperation("Invalid discussion cursor rank")
                last_id = object_id(fields[2])

        rows = await self.repository.page(kind, publication.id, parent, last_id, limit, sort, last_count, viewer_id)
        page = rows[:limit]
        next_cursor = None
        if len(rows) > limit:
            last = page[-1]
            next_cursor = str(last.id) if sort == "oldest" else f"{sort}.{last.likes_count}.{last.id}"

        result = dict(items=await comment_responses(page, viewer_id), next_cursor=next_cursor)

        return PostReplyPage(**result) if kind == "micro_post" else ArticleCommentPage(**result)

    async def get(
        self, kind: PublicationKind, publication_id: str, comment_id: str,
        viewer_id: PydanticObjectId | None = None,
    ) -> Discussion:
        """Read a visible entry or tombstone, excluding every disabled article discussion.

        :param kind: Containing publication type.
        :param publication_id: Public containing publication identifier.
        :param comment_id: Scoped comment identifier.
        :param viewer_id: Optional owner permitted to read its own archived content.
        :return: The entry after publication, branch visibility, and membership checks.
        """
        publication = await readable_discussion(kind, publication_id, viewer_id)
        comment = await self.repository.get(kind, publication.id, object_id(comment_id))

        visible = await MicroPost.aggregate([
            {"$match": {"_id": comment.id}}, *visible_post_stages(viewer_id=viewer_id), {"$limit": 1},
        ]).to_list() if comment is not None else []
        if not visible:
            raise NotFound("Comment not found")

        return comment
