"""Ownership-aware articles operations with audited transactions."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.articles.models import Article
from backend.articles.repository import ArticleRepository, ArticleStatus
from backend.articles.schemas import ArticleCreate, ArticleUpdate
from backend.articles.summary import article_summary
from backend.articles.validation import article_body_attachments, article_image_keys
from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.core.config import get_settings
from backend.core.errors import InvalidOperation, NotFound
from backend.core.resources import AppResources
from backend.core.transactions import transaction
from backend.feeds.cache import invalidate_public_feed
from backend.links.cache import enqueue_attachments
from backend.profiles.models import User
from backend.profiles.repository import ProfileRepository
from backend.publications.attachment_validation import validate_attachment_references
from backend.publications.queries import load_authors
from backend.search.sync import sync_publication
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


class ArticleService:
    """Own articles reads, mutations, and transaction boundaries."""

    def __init__(self, resources: AppResources, audit: AuditContext) -> None:
        """Initialize articles operations with infrastructure and audit metadata.

        :param resources: Application-owned database, cache, and storage clients.
        :param audit: Request metadata attached to audited operations.
        :return: None.
        """
        self.resources = resources
        self.audit = audit
        self.repository = ArticleRepository()

    async def owned(
        self,
        resource_id: str,
        owner: User,
        session: AsyncClientSession,
    ) -> Article:
        """Read ownership inside the write transaction so image updates are preserved.

        :param resource_id: String identifier of the publication to load or mutate.
        :param owner: Authenticated account owning or initiating the operation.
        :param session: MongoDB session for the caller transaction.
        :return: The undeleted publication owned by the supplied account.
        """
        item = await self.repository.get_article(publication_id(resource_id), session=session)

        if item is None or item.deleted_at is not None or item.owner_id != owner.id:
            raise NotFound("Publication not found")

        return item

    async def create_article(self, payload: ArticleCreate, owner: User) -> Article:
        """Create an audited draft after validating body and attachment references.

        :param payload: Validated request data for the operation.
        :param owner: Authenticated account owning or initiating the operation.
        :return: The persisted draft article.
        """
        if article_image_keys(payload.body):
            raise InvalidOperation("Upload article images after creating a draft")

        now = datetime.now(UTC)
        article = Article(
            owner_id=owner.id,
            title=payload.title,
            hero_layout=payload.hero_layout,
            comments_enabled=payload.comments_enabled,
            search_enabled=payload.search_enabled,
            summary=article_summary(payload.body),
            body=payload.body,
            attachments=payload.attachments,
            created_at=now,
            updated_at=now,
        )

        async with transaction(self.resources.mongo) as session:
            await validate_attachment_references(
                [*payload.attachments, *article_body_attachments(payload.body)], [], session
            )
            await article.insert(session=session)
            await record_audit(
                self.audit,
                "ARTICLE_CREATED",
                actor_id=owner.id,
                target_type="article",
                target_id=str(article.id),
                metadata={"status": "draft"},
                session=session,
            )

        await enqueue_attachments(self.resources.redis, [*article.attachments, *article_body_attachments(article.body)])
        return article

    async def edit_article(self, article_id: str, payload: ArticleUpdate, owner: User) -> Article:
        """Update content, publication settings, references, and search eligibility in one audited transaction.

        :param article_id: MongoDB identifier of the article.
        :param payload: Validated request data for the operation.
        :param owner: Authenticated account owning or initiating the operation.
        :return: The updated article.
        """
        async with transaction(self.resources.mongo) as session:
            article = await self.owned(article_id, owner, session)

            if payload.attachments is not None or payload.body is not None:
                attachments = article.attachments if payload.attachments is None else payload.attachments
                body = article.body if payload.body is None else payload.body
                await validate_attachment_references(
                    [*attachments, *article_body_attachments(body)],
                    [publication_image_url(key, "article-images") for key in article.inline_image_keys],
                    session,
                    retained=[*article.attachments, *article_body_attachments(article.body)],
                )
                article.attachments = attachments

            if payload.body is not None:
                if not article_image_keys(payload.body).issubset(set(article.inline_image_keys)):
                    raise InvalidOperation("Article body references an image not uploaded to this article")

                article.body = payload.body

            if payload.title is not None:
                article.title = payload.title

            if payload.hero_layout is not None:
                article.hero_layout = payload.hero_layout

            if payload.comments_enabled is not None:
                article.comments_enabled = payload.comments_enabled

            if payload.search_enabled is not None:
                article.search_enabled = payload.search_enabled

            article.summary = article_summary(article.body)

            article.updated_at = datetime.now(UTC)
            await article.save(session=session)
            await sync_publication(article, session)
            await record_audit(
                self.audit,
                "ARTICLE_EDITED",
                actor_id=owner.id,
                target_type="article",
                target_id=article_id,
                metadata={"fields": sorted(payload.model_fields_set)},
                session=session,
            )

        await invalidate_public_feed(self.resources.redis)

        await enqueue_attachments(self.resources.redis, [*article.attachments, *article_body_attachments(article.body)])
        return article

    async def transition(
        self,
        article_id: str,
        owner: User,
        state: ArticleStatus,
        publish_at: datetime | None = None,
    ) -> Article:
        """Change visibility and its timestamps together with the corresponding audit event.

        Publishing an already published article preserves its original timestamp.
        Search projections change in the same transaction. Draft and scheduled
        transitions clear published_at and pinned_at. Archived
        articles must be restored before a status change. Conflicts require an
        explicit reload; the transaction body is not automatically repeated.

        :param article_id: MongoDB identifier of the article.
        :param owner: Authenticated account owning or initiating the operation.
        :param state: Requested article publication state.
        :param publish_at: Future publication timestamp required for a scheduled
            transition.
        :return: The article with its resulting visibility and timestamps.
        """
        async with transaction(self.resources.mongo) as session:
            article = await self.owned(article_id, owner, session)

            if article.archived_at is not None:
                raise InvalidOperation("Unarchive this article before changing its publication status")

            if state == "published" and article.status == "published":
                return article

            now = datetime.now(UTC)

            if state == "scheduled" and (publish_at is None or publish_at <= now):
                raise InvalidOperation("Publish time must be in the future")

            if state != "published":
                article.pinned_at = None
            article.status = state
            article.published_at = now if state == "published" else None
            article.scheduled_at = publish_at if state == "scheduled" else None
            article.updated_at = now
            await article.save(session=session)
            await sync_publication(article, session)
            action = {
                "draft": "ARTICLE_UNPUBLISHED",
                "scheduled": "ARTICLE_SCHEDULED",
                "published": "ARTICLE_PUBLISHED",
            }[state]
            metadata = {"publish_at": publish_at.isoformat()} if state == "scheduled" and publish_at else {}
            await record_audit(
                self.audit,
                action,
                actor_id=owner.id,
                target_type="article",
                target_id=article_id,
                metadata=metadata,
                session=session,
            )

        await invalidate_public_feed(self.resources.redis)

        return article

    async def get_article(self, resource_id: str, viewer: User | None) -> tuple[Article, list[User]]:
        """Load a public article, or private drafts, schedules, and archives for their owner.

        :param resource_id: String identifier of the publication to load or mutate.
        :param viewer: Current account, or None for an anonymous reader.
        :return: The visible article and its author accounts in stored order.
        """
        article = await self.repository.get_article(publication_id(resource_id))

        if (
            article is None
            or article.deleted_at is not None
            or (
                (article.status != "published" or article.archived_at is not None)
                and (viewer is None or viewer.id != article.owner_id)
            )
        ):
            raise NotFound("Article not found")

        return article, await load_authors(article.author_ids)

    async def list_mine(
        self,
        owner: User,
        status: ArticleStatus | None,
        offset: int,
        limit: int,
    ) -> list[tuple[Article, list[User]]]:
        """List the owner's articles with status and offset pagination.

        :param owner: Authenticated account owning or initiating the operation.
        :param status: Optional article publication status filter.
        :param offset: Number of matching entries to skip before selecting the page.
        :param limit: Maximum number of entries to return in this page.
        :return: Owned articles paired with all their author accounts in stored order.
        """
        articles = await self.repository.list_articles(owner.id, status, offset=offset, limit=limit)
        ids = list({author_id for article in articles for author_id in article.author_ids})
        by_id = {author.id: author for author in await ProfileRepository.users_by_ids(ids)}

        if any(author_id not in by_id for article in articles for author_id in article.author_ids):
            raise NotFound("Author not found")

        return [(article, [by_id[author_id] for author_id in article.author_ids]) for article in articles]

    async def remove_cover(self, article_id: str, owner: User) -> None:
        """Detach the owned cover and queue deletion in the same transaction.

        :param article_id: Owned, undeleted article identifier.
        :param owner: Authenticated article owner.
        :return: None.
        """
        async with transaction(self.resources.mongo) as session:
            article = await self.owned(article_id, owner, session)
            if article.thumbnail_key is None:
                return

            old_key = article.thumbnail_key
            article.thumbnail_key = None
            article.updated_at = datetime.now(UTC)
            await article.save(session=session)
            await queue_deletion(get_settings().publication_bucket, old_key, session=session)
            await record_audit(
                self.audit, "ARTICLE_THUMBNAIL_REMOVED", actor_id=owner.id, target_type="article",
                target_id=article_id, session=session,
            )

        await invalidate_public_feed(self.resources.redis)

    async def delete(self, resource_id: str, owner: User) -> None:
        """Soft-delete an owned publication, remove its search projection, and queue image cleanup.

        :param resource_id: String identifier of the publication to load or mutate.
        :param owner: Authenticated account owning or initiating the operation.
        :return: None.
        """
        async with transaction(self.resources.mongo) as session:
            item = await self.owned(resource_id, owner, session)
            item.deleted_at = item.updated_at = datetime.now(UTC)
            item.pinned_at = item.archived_at = None
            await item.save(session=session)
            await sync_publication(item, session)

            keys = ([item.thumbnail_key] if item.thumbnail_key else []) + item.inline_image_keys

            for key in keys:
                await queue_deletion(get_settings().publication_bucket, key, session=session)

            await record_audit(
                self.audit,
                "ARTICLE_DELETED",
                actor_id=owner.id,
                target_type="article",
                target_id=resource_id,
                session=session,
            )

        await invalidate_public_feed(self.resources.redis)
