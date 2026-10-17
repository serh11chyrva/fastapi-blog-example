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
    publication: MicroPost | Article
    published_at: datetime

    @property
    def kind(self) -> PublicationKind:
        return "micro_post" if isinstance(self.publication, MicroPost) else "article"

    @property
    def sort_key(self) -> tuple[datetime, str, str]:
        return self.published_at, self.kind, str(self.publication.id)


class ContentRepository:
    @staticmethod
    async def get_post(
        post_id: PydanticObjectId, session: AsyncClientSession | None = None
    ) -> MicroPost | None:
        return await MicroPost.get(post_id, session=session)

    @staticmethod
    async def get_article(
        article_id: PydanticObjectId,
        session: AsyncClientSession | None = None,
    ) -> Article | None:
        return await Article.get(article_id, session=session)

    @staticmethod
    async def list_articles(
        author_id: PydanticObjectId,
        status: ArticleStatus | None = None,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Article]:
        conditions: dict[str, Any] = {"author_id": author_id, "deleted_at": None}
        if status is not None:
            conditions["status"] = status
        return (
            await Article.find(conditions)
            .sort(("updated_at", -1), ("_id", -1))
            .skip(offset)
            .limit(limit)
            .to_list()
        )

    @staticmethod
    async def load_feed_type(
        kind: PublicationKind, conditions: dict[str, Any], limit: int
    ) -> list[FeedEntry]:
        if kind == "micro_post":
            posts = (
                await MicroPost.find(conditions)
                .sort(("created_at", -1), ("_id", -1))
                .limit(limit + 1)
                .to_list()
            )
            return [FeedEntry(post, post.created_at) for post in posts]
        articles = (
            await Article.find(conditions)
            .sort(("published_at", -1), ("_id", -1))
            .limit(limit + 1)
            .to_list()
        )
        return [
            FeedEntry(article, article.published_at)
            for article in articles
            if article.published_at is not None
        ]

    @staticmethod
    async def list_publications(
        author_id: PydanticObjectId,
        kind: FeedKind,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[FeedEntry]:
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
