"""Ownership-aware posts operations with audited transactions."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

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
from backend.storage.cleanup import queue_deletion


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

        if item is None or item.deleted_at is not None or item.author_id != owner.id:
            raise NotFound("Publication not found")

        return item

    async def create_post(self, payload: MicroPostCreate, owner: User) -> MicroPost:
        """Insert a micro-post and its audit event, then invalidate the feed.

        :param payload: Validated request data for the operation.
        :param owner: Authenticated account owning or initiating the operation.
        :return: The persisted micro-post.
        """
        now = datetime.now(UTC)
        post = MicroPost(author_id=owner.id, text=payload.text, created_at=now, updated_at=now)

        async with transaction(self.resources.mongo) as session:
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

    async def edit_post(self, post_id: str, payload: MicroPostCreate, owner: User) -> MicroPost:
        """Replace an owned micro-post's text in an audited transaction.

        :param post_id: MongoDB identifier of the micro-post.
        :param payload: Validated request data for the operation.
        :param owner: Authenticated account owning or initiating the operation.
        :return: The updated micro-post.
        """
        async with transaction(self.resources.mongo) as session:
            post = await self.owned(post_id, owner, session)
            post.text = payload.text
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

    async def get_post(self, resource_id: str) -> tuple[MicroPost, User]:
        """Load a public undeleted micro-post and its author.

        :param resource_id: String identifier of the publication to load or mutate.
        :return: The micro-post and its author account.
        """
        post = await self.repository.get_post(publication_id(resource_id))

        if post is None or post.deleted_at is not None:
            raise NotFound("Post not found")

        return post, await self.author(post.author_id)

    async def delete(self, resource_id: str, owner: User) -> None:
        """Soft-delete an owned publication and queue its images for cleanup.

        :param resource_id: String identifier of the publication to load or mutate.
        :param owner: Authenticated account owning or initiating the operation.
        :return: None.
        """
        async with transaction(self.resources.mongo) as session:
            item = await self.owned(resource_id, owner, session)
            item.deleted_at = item.updated_at = datetime.now(UTC)
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

    async def author(self, author_id: PydanticObjectId) -> User:
        """Load a publication author or raise a not-found error.

        :param author_id: MongoDB identifier of the publication author.
        :return: The author account.
        """
        author = await User.get(author_id)

        if author is None:
            raise NotFound("Author not found")

        return author
