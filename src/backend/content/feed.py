"""Feed loading, batched author hydration, and optional public response caching."""

from typing import Any

from beanie import PydanticObjectId
from loguru import logger
from pydantic import ValidationError
from redis.exceptions import RedisError

from backend.content.cursors import FeedCursor
from backend.content.presenters import feed_item
from backend.content.repository import ContentRepository, FeedEntry, FeedKind, PublicationKind
from backend.content.schemas import FeedResponse
from backend.core.resources import AppResources
from backend.profiles.models import Follow, User


async def make_feed(
    resources: AppResources,
    authors: list[PydanticObjectId] | None,
    kind: FeedKind,
    cursor_text: str | None,
    limit: int,
    cache_key: str | None = None,
) -> FeedResponse:
    cursor = FeedCursor.decode(cursor_text)
    if cache_key:
        try:
            cached = await resources.redis.get(cache_key)
            if cached:
                return FeedResponse.model_validate_json(cached)
        except (RedisError, ValidationError):
            logger.warning("Public feed cache unavailable or incompatible")
    entries: list[FeedEntry] = []
    kinds: list[PublicationKind] = ["micro_post", "article"] if kind == "all" else [kind]
    for item_kind in kinds:
        conditions: dict[str, Any] = {"deleted_at": None}
        date_field = "created_at"
        if item_kind == "article":
            conditions.update(status="published", published_at={"$ne": None})
            date_field = "published_at"
        if authors is not None:
            if not authors:
                continue
            conditions["author_id"] = {"$in": authors}
        if cursor:
            conditions.update(cursor.conditions(item_kind, date_field))
        entries.extend(await ContentRepository.load_feed_type(item_kind, conditions, limit))
    entries.sort(key=lambda entry: entry.sort_key, reverse=True)
    page = entries[:limit]
    ids = list({entry.publication.author_id for entry in page})
    by_id = {author.id: author for author in await User.find({"_id": {"$in": ids}}).to_list()} if ids else {}
    items = [feed_item(entry.publication, by_id[entry.publication.author_id]) for entry in page if entry.publication.author_id in by_id]
    next_cursor = None
    if len(entries) > limit and page:
        last = page[-1]
        next_cursor = FeedCursor(last.published_at, last.kind, last.publication.id).encode()
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
    try:
        version = await resources.redis.get("feed:public:version") or "0"
    except RedisError:
        version = "0"
    key = f"feed:public:{version}:{kind}:{limit}:{cursor or 'first'}"
    return await make_feed(resources, None, kind, cursor, limit, key)


async def load_following_feed(
    resources: AppResources,
    user: User,
    kind: FeedKind,
    cursor: str | None,
    limit: int,
) -> FeedResponse:
    follows = await Follow.find(Follow.follower_id == user.id).to_list()
    return await make_feed(resources, [follow.followee_id for follow in follows], kind, cursor, limit)
