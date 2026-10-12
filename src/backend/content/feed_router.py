import base64
import json
from datetime import UTC, datetime
from typing import Literal

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query, Request, status

from backend.content.schemas import FeedItem, FeedResponse
from backend.content.repository import ContentRepository
from backend.content.urls import article_thumbnail_url, publication_image_url, share_path
from backend.core.dependencies import CurrentUser
from backend.profiles.models import Follow, User
from backend.profiles.service import ProfileService


router = APIRouter(prefix="/feeds", tags=["feeds"])
content_repository = ContentRepository()
FeedKind = Literal["all", "micro_post", "article"]


def _encode_cursor(item: FeedItem) -> str:
    value = {"time": item.published_at.isoformat(), "kind": item.kind, "id": item.id}
    return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> tuple[datetime, str, PydanticObjectId] | None:
    if not cursor:
        return None
    try:
        value = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        kind = value["kind"]
        object_id = value["id"]
        if kind not in {"micro_post", "article"} or not PydanticObjectId.is_valid(object_id):
            raise ValueError
        published_at = datetime.fromisoformat(value["time"])
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)
        return published_at, kind, PydanticObjectId(object_id)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid feed cursor") from exc


def _cursor_filter(kind: str, date_field: str, cursor: tuple[datetime, str, PydanticObjectId] | None) -> dict:
    if cursor is None:
        return {}
    timestamp, cursor_kind, object_id = cursor
    if kind < cursor_kind:
        return {date_field: {"$lte": timestamp}}
    if kind > cursor_kind:
        return {date_field: {"$lt": timestamp}}
    return {
        "$or": [
            {date_field: {"$lt": timestamp}},
            {date_field: timestamp, "_id": {"$lt": object_id}},
        ]
    }


async def _load_type(kind: str, authors: list[PydanticObjectId] | None, cursor: tuple[datetime, str, PydanticObjectId] | None, limit: int) -> list[tuple[str, object, datetime]]:
    if kind == "micro_post":
        date_field = "created_at"
        conditions: dict = {"deleted_at": None}
    else:
        date_field = "published_at"
        conditions = {"deleted_at": None, "status": "published"}
    if authors is not None:
        if not authors:
            return []
        conditions["author_id"] = {"$in": authors}
    conditions.update(_cursor_filter(kind, date_field, cursor))
    items = await content_repository.load_feed_type(kind, conditions, date_field, limit)
    return [(kind, item, getattr(item, date_field)) for item in items]


async def _make_feed(request: Request, authors: list[PydanticObjectId] | None, kind_filter: FeedKind, cursor_text: str | None, limit: int, cache_key: str | None) -> FeedResponse:
    if cache_key:
        try:
            cached = await request.app.state.redis.get(cache_key)
            if cached:
                return FeedResponse.model_validate_json(cached)
        except Exception:
            request.app.state.logger.warning("Redis unavailable while reading public feed cache")

    cursor = _decode_cursor(cursor_text)
    types = [kind_filter] if kind_filter != "all" else ["micro_post", "article"]
    pairs = []
    for kind in types:
        pairs.extend(await _load_type(kind, authors, cursor, limit))
    pairs.sort(key=lambda pair: (pair[2], pair[0], str(pair[1].id)), reverse=True)
    has_more = len(pairs) > limit
    page = pairs[:limit]
    author_ids = list({item.author_id for _, item, _ in page})
    authors_by_id = {author.id: author for author in await User.find({"_id": {"$in": author_ids}}).to_list()} if author_ids else {}
    feed_items = []
    for kind, item, published_at in page:
        author = authors_by_id.get(item.author_id)
        if author is None:
            continue
        feed_items.append(
            FeedItem(
                id=str(item.id),
                kind=kind,
                share_url=share_path(author.username, item.title if kind == "article" else item.text, item.share_id),
                title=item.title if kind == "article" else None,
                text=item.text if kind == "micro_post" else None,
                summary=item.summary if kind == "article" else None,
                thumbnail_url=article_thumbnail_url(item.thumbnail_key) if kind == "article" else None,
                images=[publication_image_url(key, "post-images") for key in item.image_keys] if kind == "micro_post" else [],
                author_id=str(author.id),
                author_username=author.username,
                author_display_name=author.display_name,
                author_avatar_url=ProfileService.avatar_url(author),
                published_at=published_at,
            )
        )
    next_cursor = _encode_cursor(feed_items[-1]) if has_more and feed_items else None
    result = FeedResponse(items=feed_items, next_cursor=next_cursor)
    if cache_key:
        try:
            await request.app.state.redis.set(cache_key, result.model_dump_json(), ex=20)
        except Exception:
            request.app.state.logger.warning("Redis unavailable while writing public feed cache")
    return result


@router.get("/public", response_model=FeedResponse)
async def public_feed(
    request: Request,
    kind: FeedKind = "all",
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
) -> FeedResponse:
    try:
        version = await request.app.state.redis.get("feed:public:version") or "0"
    except Exception:
        version = "0"
    cache_key = f"feed:public:{version}:{kind}:{limit}:{cursor or 'first'}"
    return await _make_feed(request, None, kind, cursor, limit, cache_key)


@router.get("/following", response_model=FeedResponse)
async def following_feed(
    request: Request,
    current_user: CurrentUser,
    kind: FeedKind = "all",
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
) -> FeedResponse:
    follows = await Follow.find(Follow.follower_id == current_user.id).to_list()
    authors = [item.followee_id for item in follows]
    return await _make_feed(request, authors, kind, cursor, limit, None)
