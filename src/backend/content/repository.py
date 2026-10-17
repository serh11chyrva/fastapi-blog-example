"""Beanie queries for publications and stable feed ordering."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.content.models import Article, MicroPost

type PublicationKind = Literal["micro_post", "article"]
type FeedKind = Literal["all", "micro_post", "article"]
type ArticleStatus = Literal["draft", "scheduled", "published"]


@dataclass(frozen=True, slots=True)
class FeedEntry:
    """Publication paired with the timestamp used for merged feed ordering."""

    publication: MicroPost | Article
    published_at: datetime

    @property
    def kind(self) -> PublicationKind:
        """Identify the publication type represented by this feed entry.

        :return: The micro_post or article discriminator.
        """
        return "micro_post" if isinstance(self.publication, MicroPost) else "article"

    @property
    def sort_key(self) -> tuple[datetime, str, str]:
        """Build the deterministic ordering key for a merged feed.

        :return: The publication time, type, and string document ID.
        """
        return self.published_at, self.kind, str(self.publication.id)


class ContentRepository:
    """Beanie publication queries and deterministic feed pagination."""

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
    async def get_article(
        article_id: PydanticObjectId,
        session: AsyncClientSession | None = None,
    ) -> Article | None:
        """Load an article document by its identifier.

        :param article_id: MongoDB identifier of the article.
        :param session: Optional MongoDB session for the operation or caller
            transaction.
        :return: The article, or None when absent.
        """
        return await Article.get(article_id, session=session)

    @staticmethod
    async def list_articles(
        author_id: PydanticObjectId,
        status: ArticleStatus | None = None,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Article]:
        """List an author's undeleted articles with optional status filtering.

        :param author_id: MongoDB identifier of the publication author.
        :param status: Optional article publication status filter.
        :param offset: Number of matching entries to skip before selecting the page.
        :param limit: Maximum number of entries to return in this page.
        :return: The requested page ordered by update time and ID descending.
        """
        conditions: dict[str, Any] = {"author_id": author_id, "deleted_at": None}

        if status is not None:
            conditions["status"] = status

        return await Article.find(conditions).sort(("updated_at", -1), ("_id", -1)).skip(offset).limit(limit).to_list()

    @staticmethod
    async def load_feed_type(kind: PublicationKind, conditions: dict[str, Any], limit: int) -> list[FeedEntry]:
        """Load one publication type with an extra item for cursor pagination.

        :param kind: Publication type filter: micro_post, article, or all when
            supported.
        :param conditions: MongoDB filters applied before ordering and pagination.
        :param limit: Maximum number of entries to return in this page.
        :return: Feed entries ordered newest first, up to limit plus one.
        """
        if kind == "micro_post":
            posts = await MicroPost.find(conditions).sort(("created_at", -1), ("_id", -1)).limit(limit + 1).to_list()

            return [FeedEntry(post, post.created_at) for post in posts]

        articles = await Article.find(conditions).sort(("published_at", -1), ("_id", -1)).limit(limit + 1).to_list()

        return [FeedEntry(article, article.published_at) for article in articles if article.published_at is not None]

    @staticmethod
    async def list_publications(
        author_id: PydanticObjectId,
        kind: FeedKind,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[FeedEntry]:
        """Merge an author's public posts and articles into an offset page.

        :param author_id: MongoDB identifier of the publication author.
        :param kind: Publication type filter: micro_post, article, or all when
            supported.
        :param offset: Number of matching entries to skip before selecting the page.
        :param limit: Maximum number of entries to return in this page.
        :return: The requested publication entries ordered newest first.
        """
        entries: list[FeedEntry] = []

        if kind in {"all", "micro_post"}:
            entries.extend(
                await ContentRepository.load_feed_type(
                    "micro_post",
                    {"author_id": author_id, "deleted_at": None},
                    offset + limit,
                )
            )

        if kind in {"all", "article"}:
            entries.extend(
                await ContentRepository.load_feed_type(
                    "article",
                    {
                        "author_id": author_id,
                        "deleted_at": None,
                        "status": "published",
                        "published_at": {"$ne": None},
                    },
                    offset + limit,
                )
            )

        entries.sort(key=lambda entry: entry.sort_key, reverse=True)

        return entries[offset : offset + limit]
