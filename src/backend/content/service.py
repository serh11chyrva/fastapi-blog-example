"""Publication operations with explicit ownership and audited transaction boundaries."""

from datetime import UTC, datetime
from typing import TypeVar
import re

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.content.cache import invalidate_public_feed
from backend.content.models import Article, MicroPost
from backend.content.repository import ContentRepository, ArticleStatus
from backend.content.schemas import ArticleCreate, ArticleUpdate, MicroPostCreate
from backend.content.validation import article_image_keys
from backend.core.config import get_settings
from backend.core.errors import InvalidOperation, NotFound
from backend.core.resources import AppResources
from backend.core.transactions import transaction
from backend.profiles.models import User
from backend.storage.cleanup import queue_deletion


Publication = TypeVar("Publication", MicroPost, Article)


def publication_id(value: str) -> PydanticObjectId:
    if not PydanticObjectId.is_valid(value):
        raise NotFound("Publication not found")
    return PydanticObjectId(value)


class ContentService:
    def __init__(self, resources: AppResources, audit: AuditContext) -> None:
        self.resources = resources
        self.audit = audit
        self.repository = ContentRepository()

    async def owned(
        self,
        model: type[Publication],
        resource_id: str,
        owner: User,
        session: AsyncClientSession,
    ) -> Publication:
        """Read ownership inside the write transaction so image updates are preserved."""
        item = await model.get(publication_id(resource_id), session=session)
        if item is None or item.deleted_at is not None or item.author_id != owner.id:
            raise NotFound("Publication not found")
        return item

    async def create_post(self, payload: MicroPostCreate, owner: User) -> MicroPost:
        now = datetime.now(UTC)
        post = MicroPost(author_id=owner.id, text=payload.text, created_at=now, updated_at=now)
        async with transaction(self.resources.mongo) as session:
            await post.insert(session=session)
            await record_audit(self.audit, "MICRO_POST_CREATED", actor_id=owner.id, target_type="micro_post", target_id=str(post.id), session=session)
        await invalidate_public_feed(self.resources.redis)
        return post

    async def edit_post(self, post_id: str, payload: MicroPostCreate, owner: User) -> MicroPost:
        async with transaction(self.resources.mongo) as session:
            post = await self.owned(MicroPost, post_id, owner, session)
            post.text = payload.text
            post.updated_at = datetime.now(UTC)
            await post.save(session=session)
            await record_audit(self.audit, "MICRO_POST_EDITED", actor_id=owner.id, target_type="micro_post", target_id=post_id, session=session)
        await invalidate_public_feed(self.resources.redis)
        return post

    async def delete(self, model: type[Publication], resource_id: str, owner: User) -> None:
        async with transaction(self.resources.mongo) as session:
            item = await self.owned(model, resource_id, owner, session)
            item.deleted_at = item.updated_at = datetime.now(UTC)
            await item.save(session=session)
            if isinstance(item, MicroPost):
                keys, target_type, action = item.image_keys, "micro_post", "MICRO_POST_DELETED"
            else:
                keys = ([item.thumbnail_key] if item.thumbnail_key else []) + item.inline_image_keys
                target_type, action = "article", "ARTICLE_DELETED"
            for key in keys:
                await queue_deletion(get_settings().publication_bucket, key, session=session)
            await record_audit(self.audit, action, actor_id=owner.id, target_type=target_type, target_id=resource_id, session=session)
        await invalidate_public_feed(self.resources.redis)

    async def create_article(self, payload: ArticleCreate, owner: User) -> Article:
        if article_image_keys(payload.body):
            raise InvalidOperation("Upload article images after creating a draft")
        now = datetime.now(UTC)
        article = Article(author_id=owner.id, title=payload.title, summary=payload.summary, body=payload.body, created_at=now, updated_at=now)
        async with transaction(self.resources.mongo) as session:
            await article.insert(session=session)
            await record_audit(self.audit, "ARTICLE_CREATED", actor_id=owner.id, target_type="article", target_id=str(article.id), metadata={"status": "draft"}, session=session)
        return article

    async def edit_article(self, article_id: str, payload: ArticleUpdate, owner: User) -> Article:
        async with transaction(self.resources.mongo) as session:
            article = await self.owned(Article, article_id, owner, session)
            if payload.body is not None:
                if not article_image_keys(payload.body).issubset(set(article.inline_image_keys)):
                    raise InvalidOperation("Article body references an image not uploaded to this article")
                article.body = payload.body
            if payload.title is not None:
                article.title = payload.title
            if payload.summary is not None:
                article.summary = payload.summary
            article.updated_at = datetime.now(UTC)
            await article.save(session=session)
            await record_audit(self.audit, "ARTICLE_EDITED", actor_id=owner.id, target_type="article", target_id=article_id, metadata={"fields": sorted(payload.model_fields_set)}, session=session)
        await invalidate_public_feed(self.resources.redis)
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
        Draft and scheduled transitions clear published_at. Conflicts require an
        explicit reload; the transaction body is not automatically repeated.
        """
        async with transaction(self.resources.mongo) as session:
            article = await self.owned(Article, article_id, owner, session)
            if state == "published" and article.status == "published":
                return article
            now = datetime.now(UTC)
            if state == "scheduled" and (publish_at is None or publish_at <= now):
                raise InvalidOperation("Publish time must be in the future")
            article.status = state
            article.published_at = now if state == "published" else None
            article.scheduled_at = publish_at if state == "scheduled" else None
            article.updated_at = now
            await article.save(session=session)
            action = {"draft": "ARTICLE_UNPUBLISHED", "scheduled": "ARTICLE_SCHEDULED", "published": "ARTICLE_PUBLISHED"}[state]
            metadata = {"publish_at": publish_at.isoformat()} if state == "scheduled" and publish_at else {}
            await record_audit(self.audit, action, actor_id=owner.id, target_type="article", target_id=article_id, metadata=metadata, session=session)
        await invalidate_public_feed(self.resources.redis)
        return article


    async def get_post(self, resource_id: str) -> tuple[MicroPost, User]:
        post = await self.repository.get_post(publication_id(resource_id))
        if post is None or post.deleted_at is not None:
            raise NotFound("Post not found")
        return post, await self.author(post.author_id)

    async def get_article(self, resource_id: str, viewer: User | None) -> tuple[Article, User]:
        article = await self.repository.get_article(publication_id(resource_id))
        if article is None or article.deleted_at is not None or (article.status != "published" and (viewer is None or viewer.id != article.author_id)):
            raise NotFound("Article not found")
        return article, await self.author(article.author_id)

    async def author(self, author_id: PydanticObjectId) -> User:
        author = await User.get(author_id)
        if author is None:
            raise NotFound("Author not found")
        return author

    async def shared(self, username: str, slug: str) -> tuple[MicroPost | Article, User]:
        share_id = slug.rsplit("--", 1)[-1]
        if not re.fullmatch(r"[0-9a-f]{32}", share_id):
            raise NotFound("Publication not found")
        author = await User.find_one(User.username == username.lower().removeprefix("@"))
        if author is None:
            raise NotFound("Publication not found")
        conditions = {"author_id": author.id, "share_id": share_id, "deleted_at": None}
        post = await MicroPost.find_one(conditions)
        if post is not None:
            return post, author
        article = await Article.find_one({**conditions, "status": "published"})
        if article is None:
            raise NotFound("Publication not found")
        return article, author

    async def list_mine(self, owner: User, status: ArticleStatus | None, offset: int, limit: int) -> list[Article]:
        return await self.repository.list_articles(owner.id, status, offset=offset, limit=limit)
