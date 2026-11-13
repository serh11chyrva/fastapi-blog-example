"""Beanie queries for publications and stable feed ordering."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from beanie import PydanticObjectId

from backend.articles.models import Article
from backend.articles.repository import ArticleRepository
from backend.interactions.models import PublicationInteraction
from backend.posts.models import MicroPost
from backend.posts.visibility import visible_post_stages
from backend.posts.repository import PostRepository

type PublicationKind = Literal["micro_post", "article", "repost"]
type FeedKind = Literal["all", "micro_post", "article"]


@dataclass(frozen=True, slots=True)
class FeedEntry:
    """Original publication paired with its own event time or a separate repost edge."""

    publication: MicroPost | Article
    published_at: datetime
    repost: PublicationInteraction | None = None

    @property
    def kind(self) -> PublicationKind:
        """Identify the original or repost event represented by this feed entry.

        :return: The micro_post, article, or repost event discriminator.
        """
        if self.repost is not None:
            return "repost"

        return "micro_post" if isinstance(self.publication, MicroPost) else "article"

    @property
    def object_id(self) -> PydanticObjectId:
        """Read the event identity used to paginate originals and reposts independently.

        :return: Repost relationship ID for reposts, otherwise the original publication ID.
        """
        return self.repost.id if self.repost is not None else self.publication.id

    @property
    def sort_key(self) -> tuple[datetime, str, str]:
        """Build the deterministic ordering key for a merged feed.

        :return: The event time, event kind, and original or repost document ID.
        """
        return self.published_at, self.kind, str(self.object_id)


class FeedRepository:
    """Coordinate feature repositories for deterministic mixed publication pages."""

    @staticmethod
    async def load_feed_type(
        kind: PublicationKind, conditions: dict[str, Any], limit: int,
        group_for_profile: PydanticObjectId | None = None,
    ) -> list[FeedEntry]:
        """Load one publication type with an extra item for cursor pagination.

        :param kind: Event type to load: micro_post, article, or repost.
        :param conditions: MongoDB filters applied before ordering and pagination.
        :param limit: Maximum number of entries to return in this page.
        :param group_for_profile: Optional profile whose eligible self-replies are suppressed before pagination.
        :return: Feed entries ordered newest first, up to limit plus one.
        """
        if kind == "repost":
            rows = await PublicationInteraction.aggregate([
                {"$match": {"$and": [{"action": "repost", "publication_kind": "micro_post"}, conditions]}},
                {"$sort": {"created_at": -1, "_id": -1}},
                {"$lookup": {
                    "from": "micro_posts", "localField": "publication_id", "foreignField": "_id", "as": "original",
                }},
                {"$unwind": "$original"},
                {"$match": {"original.deleted_at": None}},
                *visible_post_stages("original"),
                {"$limit": limit + 1},
            ]).to_list()

            return [
                FeedEntry(
                    MicroPost.model_validate(row["original"]), row["created_at"],
                    PublicationInteraction.model_validate({key: value for key, value in row.items() if key != "original"}),
                )
                for row in rows
            ]

        if kind == "micro_post":
            posts = await PostRepository.load_feed(conditions, limit, group_for_profile)

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

        :param author_id: Account credited as the owner or a featured author.
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
                    {"$or": [{"owner_id": author_id}, {"featured_author_ids": author_id}], "deleted_at": None},
                    offset + limit,
                )
            )

        if kind in {"all", "article"}:
            entries.extend(
                await FeedRepository.load_feed_type(
                    "article",
                    {
                        "$or": [{"owner_id": author_id}, {"featured_author_ids": author_id}],
                        "deleted_at": None,
                        "status": "published",
                        "published_at": {"$ne": None},
                    },
                    offset + limit,
                )
            )

        entries.sort(key=lambda entry: entry.sort_key, reverse=True)

        return entries[offset : offset + limit]
