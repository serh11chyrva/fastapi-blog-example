"""Ownership-aware posts operations with audited transactions."""

from datetime import UTC, datetime
from uuid import UUID

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import DuplicateKeyError

from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.core.config import get_settings
from backend.core.errors import NotFound
from backend.core.resources import AppResources
from backend.core.transactions import transaction
from backend.feeds.cache import invalidate_public_feed
from backend.posts.models import MicroPost
from backend.posts.repository import PostRepository
from backend.posts.schemas import MicroPostCreate
from backend.profiles.models import User
from backend.publications.attachment_validation import validate_attachment_references
from backend.publications.queries import load_authors
from backend.publications.access import public_publication
from backend.storage.cleanup import queue_deletion
from backend.storage.urls import publication_image_url


def publication_id(value: str) -> PydanticObjectId:
    """Parse a publication identifier or raise a not-found error.

    :param value: String publication identifier supplied by the caller.
    :return: The validated MongoDB ObjectId.
    """
    if not PydanticObjectId.is_valid(value):
        raise NotFound("Publication not found")

    return PydanticObjectId(value)


class PostService:
    """Own posts reads, mutations, and transaction boundaries."""

    def __init__(self, resources: AppResources, audit: AuditContext) -> None:
        """Initialize posts operations with infrastructure and audit metadata.

        :param resources: Application-owned database, cache, and storage clients.
        :param audit: Request metadata attached to audited operations.
        :return: None.
        """
        self.resources = resources
        self.audit = audit
        self.repository = PostRepository()

    async def owned(
        self,
        resource_id: str,
        owner: User,
        session: AsyncClientSession,
    ) -> MicroPost:
        """Read ownership inside the write transaction so image updates are preserved.

        :param resource_id: String identifier of the publication to load or mutate.
        :param owner: Authenticated account owning or initiating the operation.
        :param session: MongoDB session for the caller transaction.
        :return: The undeleted publication owned by the supplied account.
        """
        item = await self.repository.get_post(publication_id(resource_id), session=session)

        if item is None or item.deleted_at is not None or item.owner_id != owner.id:
            raise NotFound("Publication not found")

        if item.reply is not None:
            await public_publication(item.reply.kind, str(item.reply.publication_id), session, touch=True)

        return item

    async def create_post(self, payload: MicroPostCreate, owner: User) -> MicroPost:
        """Insert a micro-post and its audit event, then invalidate the feed.

        :param payload: Validated request data for the operation.
        :param owner: Authenticated account owning or initiating the operation.
        :return: The persisted micro-post.
        """
        now = datetime.now(UTC)
        post = MicroPost(
            owner_id=owner.id, text=payload.text, attachments=payload.attachments, created_at=now, updated_at=now
        )

        async with transaction(self.resources.mongo) as session:
            await validate_attachment_references(payload.attachments, [], session)
            await post.insert(session=session)
            await record_audit(
                self.audit,
                "MICRO_POST_CREATED",
                actor_id=owner.id,
                target_type="micro_post",
                target_id=str(post.id),
                session=session,
            )

        await invalidate_public_feed(self.resources.redis)

        return post

    async def create_draft(self, key: UUID, owner: User) -> MicroPost:
        """Reserve a private upload target, returning the same target on retries.

        :param key: Client-generated key retained for one compose attempt.
        :param owner: Authenticated account owning the private target.
        :return: The staging post, or its published result after a completed retry.
        """
        draft_key = f"{owner.id}:{key}"
        existing = await MicroPost.find_one({"draft_key": draft_key})
        if existing is not None:
            if existing.deleted_at is not None:
                raise NotFound("This draft expired; start a new post")
            return existing
        now = datetime.now(UTC)
        post = MicroPost(owner_id=owner.id, text="", pending=True, draft_key=draft_key,
                         created_at=now, updated_at=now)
        try:
            await post.insert()
        except DuplicateKeyError:
            existing = await MicroPost.find_one({"draft_key": draft_key})
            if existing is None or existing.deleted_at is not None:
                raise NotFound("This draft expired; start a new post") from None
            return existing
        return post

    async def edit_post(self, post_id: str, payload: MicroPostCreate, owner: User) -> MicroPost:
        """Replace owned post text and supplied attachments in one audited transaction.

        :param post_id: MongoDB identifier of the micro-post.
        :param payload: Validated request data for the operation.
        :param owner: Authenticated account owning or initiating the operation.
        :return: The updated micro-post.
        """
        async with transaction(self.resources.mongo) as session:
            post = await self.owned(post_id, owner, session)

            if "attachments" in payload.model_fields_set:
                await validate_attachment_references(
                    payload.attachments,
                    [publication_image_url(key, "post-images") for key in post.image_keys],
                    session,
                    retained=post.attachments,
                    post_id=post.id,
                )
                post.attachments = payload.attachments

            post.text = payload.text
            if post.pending:
                post.pending = False
                post.created_at = datetime.now(UTC)
            post.updated_at = datetime.now(UTC)
            await post.save(session=session)
            await record_audit(
                self.audit,
                "MICRO_POST_EDITED",
                actor_id=owner.id,
                target_type="micro_post",
                target_id=post_id,
                session=session,
            )

        await invalidate_public_feed(self.resources.redis)

        return post

    async def get_post(self, resource_id: str) -> tuple[MicroPost, list[User]]:
        """Load a public undeleted micro-post and its authors in stored order.

        :param resource_id: String identifier of the publication to load or mutate.
        :return: The micro-post and its author accounts in stored order.
        """
        post = await public_publication("micro_post", resource_id)

        return post, await load_authors(post.author_ids)

    async def delete(self, resource_id: str, owner: User) -> None:
        """Soft-delete an owned publication and queue its images for cleanup.

        :param resource_id: String identifier of the publication to load or mutate.
        :param owner: Authenticated account owning or initiating the operation.
        :return: None.
        """
        async with transaction(self.resources.mongo) as session:
            item = await self.owned(resource_id, owner, session)
            item.deleted_at = item.updated_at = datetime.now(UTC)
            if item.reply is not None:
                item.text = ""
            await item.save(session=session)

            keys = item.image_keys

            for key in keys:
                await queue_deletion(get_settings().publication_bucket, key, session=session)

            await record_audit(
                self.audit,
                "MICRO_POST_DELETED",
                actor_id=owner.id,
                target_type="micro_post",
                target_id=resource_id,
                session=session,
            )

        await invalidate_public_feed(self.resources.redis)
