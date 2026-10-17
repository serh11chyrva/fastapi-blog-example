"""Beanie queries for publications and stable feed ordering."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from beanie import PydanticObjectId

from backend.articles.models import Article
from backend.articles.repository import ArticleRepository
from backend.posts.models import MicroPost
from backend.posts.repository import PostRepository

type PublicationKind = Literal["micro_post", "article"]
type FeedKind = Literal["all", "micro_post", "article"]


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


class FeedRepository:
    """Coordinate feature repositories for deterministic mixed publication pages."""

    @staticmethod
    async def load_feed_type(kind: PublicationKind, conditions: dict[str, Any], limit: int) -> list[FeedEntry]:
        """Load one publication type with an extra item for cursor pagination.

        :param kind: Publication type to load: micro_post or article.
        :param conditions: MongoDB filters applied before ordering and pagination.
        :param limit: Maximum number of entries to return in this page.
        :return: Feed entries ordered newest first, up to limit plus one.
        """
        if kind == "micro_post":
            posts = await PostRepository.load_feed(conditions, limit)

            return [FeedEntry(post, post.created_at) for post in posts]

        articles = await ArticleRepository.load_feed(conditions, limit)

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
                await FeedRepository.load_feed_type(
                    "micro_post",
                    {"author_id": author_id, "deleted_at": None},
                    offset + limit,
                )
            )

        if kind in {"all", "article"}:
            entries.extend(
                await FeedRepository.load_feed_type(
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
