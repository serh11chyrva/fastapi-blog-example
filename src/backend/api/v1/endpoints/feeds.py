"""HTTP query parameters for chronological feeds."""

from fastapi import APIRouter, Query

from backend.auth.dependencies import CurrentUser
from backend.content.feed import load_public_feed, load_following_feed
from backend.content.repository import FeedKind
from backend.content.schemas import FeedResponse
from backend.api.metadata import documented_responses
from backend.core.resources import Resources


router = APIRouter(prefix="/feeds")


@router.get(
    "/public",
    response_model=FeedResponse,
    summary='Read the public feed',
    description='Chronological mixed feed of public micro-posts and published articles.',
    tags=['Feeds'],
    responses=documented_responses(503),
)
async def public_feed(
    resources: Resources,
    kind: FeedKind = "all",
    cursor: str | None = Query(default=None, max_length=2048),
    limit: int = Query(default=20, ge=1, le=50, description="Feed page size from 1 to 50; defaults to 20."),
) -> FeedResponse:
    return await load_public_feed(resources, kind, cursor, limit)


@router.get(
    "/following",
    response_model=FeedResponse,
    summary='Read the following feed',
    description='Chronological mixed feed from followed authors; requires a session cookie.',
    tags=['Feeds'],
    responses=documented_responses(401, 503),
)
async def following_feed(
    resources: Resources,
    current_user: CurrentUser,
    kind: FeedKind = "all",
    cursor: str | None = Query(default=None, max_length=2048),
    limit: int = Query(default=20, ge=1, le=50, description="Feed page size from 1 to 50; defaults to 20."),
) -> FeedResponse:
    return await load_following_feed(resources, current_user, kind, cursor, limit)
