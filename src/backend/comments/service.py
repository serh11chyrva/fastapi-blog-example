"""Audited comment mutations and visibility-aware discussion reads."""

from datetime import UTC, datetime

from beanie import PydanticObjectId

from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.comments.models import ArticleComment, PostReply
from backend.comments.presenters import comment_responses
from backend.comments.repository import CommentRepository, Discussion
from backend.comments.schemas import ArticleCommentPage, CommentText, PostReplyPage
from backend.core.errors import InvalidOperation, NotFound
from backend.core.resources import AppResources
from backend.core.transactions import transaction
from backend.profiles.models import User
from backend.publications.access import PublicationKind, object_id, public_publication


class CommentService:
    """Own flat article discussions and unbounded-depth, incrementally loaded post trees."""

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
        """Create a comment or reply and audit it in the same guarded transaction.

        :param kind: Containing publication type; article parents are forbidden.
        :param publication_id: Public post or article identifier.
        :param payload: Validated plain text to store.
        :param owner: Authenticated account authoring the comment.
        :param parent_id: Optional undeleted parent in this post, never another publication.
        :return: The persisted flat comment or immutable reply-tree position.
        """
        if kind == "article" and parent_id is not None:
            raise InvalidOperation("Article comments cannot have replies")

        async with transaction(self.resources.mongo) as session:
            publication = await public_publication(kind, publication_id, session, touch=True)
            now = datetime.now(UTC)
            common = dict(author_id=owner.id, text=payload.text, created_at=now, updated_at=now)
            comment: Discussion

            if kind == "micro_post":
                reply_id = PydanticObjectId()
                parent = None

                if parent_id is not None:
                    parent = await self.repository.get(kind, publication.id, object_id(parent_id), session)

                    if not isinstance(parent, PostReply) or parent.deleted_at is not None:
                        raise NotFound("Parent reply not found")

                    await parent.update({"$inc": {"reply_revision": 1}}, session=session)

                comment = PostReply(
                    **common,
                    id=reply_id,
                    post_id=publication.id,
                    parent_id=parent.id if parent else None,
                    root_id=parent.root_id if parent else reply_id,
                    depth=parent.depth + 1 if parent else 0,
                )
            else:
                comment = ArticleComment(**common, article_id=publication.id)

            await comment.insert(session=session)
            await record_audit(
                self.audit,
                "COMMENT_CREATED",
                actor_id=owner.id,
                target_type="post_reply" if kind == "micro_post" else "article_comment",
                target_id=str(comment.id),
                metadata={"publication_id": publication_id},
                session=session,
            )

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
        async with transaction(self.resources.mongo) as session:
            publication = await public_publication(kind, publication_id, session, touch=True)
            comment = await self.repository.get(kind, publication.id, object_id(comment_id), session)

            if comment is None or comment.author_id != owner.id:
                raise NotFound("Comment not found")

            if comment.deleted_at is not None:
                if payload is None:
                    return comment

                raise NotFound("Comment not found")

            comment.updated_at = datetime.now(UTC)

            if payload is None:
                comment.text = ""
                comment.deleted_at = comment.updated_at
            else:
                comment.text = payload.text

            await comment.save(session=session)
            await record_audit(
                self.audit,
                "COMMENT_DELETED" if payload is None else "COMMENT_EDITED",
                actor_id=owner.id,
                target_type="post_reply" if kind == "micro_post" else "article_comment",
                target_id=comment_id,
                metadata={"publication_id": publication_id},
                session=session,
            )

        return comment

    async def page(
        self,
        kind: PublicationKind,
        publication_id: str,
        parent_id: str | None,
        cursor: str | None,
        limit: int,
    ) -> PostReplyPage | ArticleCommentPage:
        """Read one post-tree level or a flat article discussion without loading descendants recursively.

        :param kind: Containing publication type.
        :param publication_id: Public containing publication identifier.
        :param parent_id: Optional post parent reply; omission selects roots. Article parent IDs are rejected.
        :param cursor: Last returned ObjectId, or None for the first oldest-first page.
        :param limit: Bounded page size supplied by the HTTP adapter.
        :return: Typed discussion page with a continuation cursor when another row exists.
        """
        if kind == "article" and parent_id is not None:
            raise InvalidOperation("Article comments cannot have replies")

        publication = await public_publication(kind, publication_id)
        parent = object_id(parent_id) if parent_id is not None else None

        if parent is not None and await self.repository.get(kind, publication.id, parent) is None:
            raise NotFound("Parent reply not found")

        rows = await self.repository.page(kind, publication.id, parent, object_id(cursor) if cursor else None, limit)
        page = rows[:limit]
        result = dict(
            items=await comment_responses(page),
            next_cursor=str(page[-1].id) if len(rows) > limit else None,
        )

        return PostReplyPage(**result) if kind == "micro_post" else ArticleCommentPage(**result)

    async def get(self, kind: PublicationKind, publication_id: str, comment_id: str) -> Discussion:
        """Read a single visible discussion entry, including a deleted thread tombstone.

        :param kind: Containing publication type.
        :param publication_id: Public containing publication identifier.
        :param comment_id: Scoped comment identifier.
        :return: The entry after publication visibility and publication membership checks.
        """
        publication = await public_publication(kind, publication_id)
        comment = await self.repository.get(kind, publication.id, object_id(comment_id))

        if comment is None:
            raise NotFound("Comment not found")

        return comment
