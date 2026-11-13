"""Feed loading, batched author hydration, and optional public response caching."""

from typing import Any

from beanie import PydanticObjectId
from loguru import logger
from pydantic import ValidationError
from redis.exceptions import RedisError

from backend.articles.models import Article
from backend.core.resources import AppResources
from backend.feeds.cursors import FeedCursor
from backend.feeds.presenters import feed_item, repost_item
from backend.feeds.repository import FeedEntry, FeedKind, FeedRepository, PublicationKind
from backend.feeds.schemas import FeedResponse
from backend.posts.models import MicroPost
from backend.posts.threads import attach_thread_previews
from backend.posts.visibility import visible_post_stages
from backend.profiles.models import Follow, User
from backend.profiles.repository import ProfileRepository


async def current_cached_feed(page: FeedResponse) -> FeedResponse | None:
    """Recheck cached originals in batches so failed invalidation cannot expose archives.

    :param page: Parsed public feed page read from Redis.
    :return: The page with current pin state, or None when it must be rebuilt.
    """
    originals = [item.post if item.kind == "repost" else item for item in page.items]
    if any(not PydanticObjectId.is_valid(item.id) for item in originals):
        return None
    post_ids = [PydanticObjectId(item.id) for item in originals if item.kind == "micro_post"]
    article_ids = [PydanticObjectId(item.id) for item in originals if item.kind == "article"]
    rows = await MicroPost.aggregate([
        {"$match": {"_id": {"$in": post_ids}, "deleted_at": None}}, *visible_post_stages(),
    ]).to_list() if post_ids else []
    current = {("micro_post", str(row["_id"])): MicroPost.model_validate(row) for row in rows}
    articles = await Article.find({
        "_id": {"$in": article_ids}, "deleted_at": None, "archived_at": None, "status": "published",
    }).to_list() if article_ids else []
    current.update({("article", str(item.id)): item for item in articles})
    for original in originals:
        publication = current.get((original.kind, original.id))
        if publication is None:
            return None
        original.pinned_at = publication.pinned_at
        original.archived_at = None
        original.read_only = False
    await attach_thread_previews(
        [item for item in page.items if item.kind == "micro_post" and item.reply is None],
        [item for item in current.values() if isinstance(item, MicroPost) and item.reply is None],
    )
    return page


async def make_feed(
    resources: AppResources,
    authors: list[PydanticObjectId] | None,
    kind: FeedKind,
    cursor_text: str | None,
    limit: int,
    cache_key: str | None = None,
) -> FeedResponse:
    """Merge originals and repost events into a page and batch their author and reposter reads.

    :param resources: Application-owned database, cache, and storage clients.
    :param authors: Allowed credited original authors or reposting accounts, or None to include all public events.
    :param kind: Publication type filter: micro_post, article, or all when supported.
    :param cursor_text: Opaque cursor from the preceding feed page, if any.
    :param limit: Maximum number of entries to return in this page.
    :param cache_key: Optional Redis key for caching the assembled page.
    :return: The feed items and optional continuation cursor.
    """
    cursor = FeedCursor.decode(cursor_text)

    if cache_key:
        try:
            cached = await resources.redis.get(cache_key)

            if cached:
                current = await current_cached_feed(FeedResponse.model_validate_json(cached))
                if current is not None:
                    return current
        except (RedisError, ValidationError):
            logger.warning("Public feed cache unavailable or incompatible")

    entries: list[FeedEntry] = []
    kinds: list[PublicationKind] = ["micro_post", "article", "repost"] if kind == "all" else [kind]

    if kind == "micro_post":
        kinds.append("repost")

    for item_kind in kinds:
        conditions: dict[str, Any] = {"deleted_at": None}
        date_field = "created_at"

        if item_kind == "micro_post":
            conditions["reply"] = None

        if item_kind == "article":
            conditions.update(status="published", published_at={"$ne": None})
            date_field = "published_at"

        if authors is not None:
            if not authors:
                continue

            if item_kind == "repost":
                conditions["user_id"] = {"$in": authors}
            else:
                conditions["$or"] = [
                    {"owner_id": {"$in": authors}},
                    {"featured_author_ids": {"$in": authors}},
                ]

        if cursor:
            conditions = {"$and": [conditions, cursor.conditions(item_kind, date_field)]}

        entries.extend(await FeedRepository.load_feed_type(item_kind, conditions, limit))

    entries.sort(key=lambda entry: entry.sort_key, reverse=True)
    page = entries[:limit]
    ids = list({author_id for entry in page for author_id in entry.publication.author_ids})
    ids.extend(entry.repost.user_id for entry in page if entry.repost is not None)
    by_id = {author.id: author for author in await ProfileRepository.users_by_ids(ids)} if ids else {}
    items = []

    for entry in page:
        if any(author_id not in by_id for author_id in entry.publication.author_ids):
            continue

        cards = [by_id[author_id] for author_id in entry.publication.author_ids]

        if entry.repost is None:
            items.append(feed_item(entry.publication, cards))
        elif isinstance(entry.publication, MicroPost) and entry.repost.user_id in by_id:
            items.append(repost_item(entry.publication, cards, entry.repost, by_id[entry.repost.user_id]))

    next_cursor = None

    if len(entries) > limit and page:
        last = page[-1]
        next_cursor = FeedCursor(last.published_at, last.kind, last.object_id).encode()

    await attach_thread_previews(
        [item for item in items if item.kind == "micro_post" and item.reply is None],
        [entry.publication for entry in page if entry.repost is None
         and isinstance(entry.publication, MicroPost) and entry.publication.reply is None],
    )
    result = FeedResponse(items=items, next_cursor=next_cursor)

    if cache_key:
        try:
            await resources.redis.set(cache_key, result.model_dump_json(), ex=20)
        except RedisError:
            logger.warning("Redis unavailable while caching the public feed")

    return result


async def load_public_feed(
    resources: AppResources,
    kind: FeedKind,
    cursor: str | None,
    limit: int,
) -> FeedResponse:
    """Load a public feed page using the current cache version.

    :param resources: Application-owned database, cache, and storage clients.
    :param kind: Publication type filter: micro_post, article, or all when supported.
    :param cursor: Opaque cursor from the preceding feed page, if any.
    :param limit: Maximum number of entries to return in this page.
    :return: The requested public feed page.
    """
    try:
        version = await resources.redis.get("feed:public:version") or "0"
    except RedisError:
        version = "0"

    key = f"feed:public:threads-v1:{version}:{kind}:{limit}:{cursor or 'first'}"

    return await make_feed(resources, None, kind, cursor, limit, key)


async def load_following_feed(
    resources: AppResources,
    user: User,
    kind: FeedKind,
    cursor: str | None,
    limit: int,
) -> FeedResponse:
    """Load original publications and repost events attributed to followed accounts.

    :param resources: Application-owned database, cache, and storage clients.
    :param user: User account used by the operation.
    :param kind: Publication type filter: micro_post, article, or all when supported.
    :param cursor: Opaque cursor from the preceding feed page, if any.
    :param limit: Maximum number of entries to return in this page.
    :return: The requested following feed page.
    """
    follows = await Follow.find(Follow.follower_id == user.id).to_list()

    return await make_feed(resources, [follow.followee_id for follow in follows], kind, cursor, limit)
