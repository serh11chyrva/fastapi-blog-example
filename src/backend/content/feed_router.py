"""HTTP query parameters for chronological feeds."""

from backend.core.api_metadata import documented_responses

from fastapi import APIRouter, Query
from redis.exceptions import RedisError

from backend.auth.dependencies import CurrentUser
from backend.content.feed import make_feed
from backend.content.repository import FeedKind
from backend.content.schemas import FeedResponse
from backend.core.resources import Resources
from backend.profiles.models import Follow


router = APIRouter(prefix="/feeds")


@router.get(
    "/public",
    response_model=FeedResponse,
    summary='Read the public feed',
    description='Chronological mixed feed of public micro-posts and published articles.',
    tags=['Feeds'],
    responses=documented_responses(503),
)
async def public_feed(resources: Resources, kind: FeedKind = "all", cursor: str | None = Query(default=None, max_length=2048), limit: int = Query(default=20, ge=1, le=50, description="Feed page size from 1 to 50; defaults to 20.")) -> FeedResponse:
    try:
        version = await resources.redis.get("feed:public:version") or "0"
    except RedisError:
        version = "0"
    key = f"feed:public:{version}:{kind}:{limit}:{cursor or 'first'}"
    return await make_feed(resources, None, kind, cursor, limit, key)


@router.get(
    "/following",
    response_model=FeedResponse,
    summary='Read the following feed',
    description='Chronological mixed feed from followed authors; requires a session cookie.',
    tags=['Feeds'],
    responses=documented_responses(401, 503),
)
async def following_feed(resources: Resources, current_user: CurrentUser, kind: FeedKind = "all", cursor: str | None = Query(default=None, max_length=2048), limit: int = Query(default=20, ge=1, le=50, description="Feed page size from 1 to 50; defaults to 20.")) -> FeedResponse:
    follows = await Follow.find(Follow.follower_id == current_user.id).to_list()
    return await make_feed(resources, [follow.followee_id for follow in follows], kind, cursor, limit)
