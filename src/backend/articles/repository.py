"""Beanie queries owned by the feature."""

from typing import Any, Literal

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.articles.models import Article

type ArticleStatus = Literal["draft", "scheduled", "published"]


class ArticleRepository:
    """Persistence queries for articles."""

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
        owner_id: PydanticObjectId,
        status: ArticleStatus | None = None,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Article]:
        """List an owner's unarchived, undeleted articles with optional status filtering.

        :param owner_id: MongoDB identifier of the publication owner.
        :param status: Optional article publication status filter.
        :param offset: Number of matching entries to skip before selecting the page.
        :param limit: Maximum number of entries to return in this page.
        :return: The requested page ordered by update time and ID descending.
        """
        conditions: dict[str, Any] = {"owner_id": owner_id, "deleted_at": None, "archived_at": None}

        if status is not None:
            conditions["status"] = status

        return await Article.find(conditions).sort(("updated_at", -1), ("_id", -1)).skip(offset).limit(limit).to_list()

    @staticmethod
    async def load_feed(conditions: dict[str, Any], limit: int) -> list[Article]:
        """Load a bounded publication page with one continuation candidate.

        :param conditions: Visibility, author, and cursor filters supplied by the feed coordinator.
        :param limit: Page size before the extra continuation candidate.
        :return: Documents ordered by publication time and identifier descending.
        """
        return await Article.find({"$and": [conditions, {"archived_at": None}]}).sort(
            ("published_at", -1), ("_id", -1),
        ).limit(limit + 1).to_list()

    @staticmethod
    async def find_shared(owner_id: PydanticObjectId, share_id: str) -> Article | None:
        """Find a published, undeleted article; the caller must enforce archive visibility.

        :param owner_id: Account owning the publication.
        :param share_id: Persisted stable share identity.
        :return: The article, possibly archived, or None when absent or unpublished.
        """
        return await Article.find_one(
            {"owner_id": owner_id, "share_id": share_id, "deleted_at": None, "status": "published"}
        )
