"""HTTP query parameters for chronological feeds."""

from fastapi import APIRouter, Query

from backend.api.metadata import documented_responses
from backend.auth.dependencies import CurrentUser
from backend.core.resources import Resources
from backend.feeds.repository import FeedKind
from backend.feeds.schemas import FeedResponse
from backend.feeds.service import load_following_feed, load_public_feed

router = APIRouter(prefix="/feeds")


@router.get(
    "/public",
    response_model=FeedResponse,
    summary="Read the public feed",
    description="Chronological mixed feed of public micro-posts and published articles.",
    tags=["Feeds"],
    responses=documented_responses(503),
)
async def public_feed(
    resources: Resources,
    kind: FeedKind = "all",
    cursor: str | None = Query(default=None, max_length=2048),
    limit: int = Query(
        default=20,
        ge=1,
        le=50,
        description="Feed page size from 1 to 50; defaults to 20.",
    ),
) -> FeedResponse:
    """Read a cursor-paginated page of public publications.

    :param resources: Application-owned database, cache, and storage clients.
    :param kind: Publication type filter: micro_post, article, or all when supported.
    :param cursor: Opaque cursor from the preceding feed page, if any.
    :param limit: Maximum number of entries to return in this page.
    :return: The public feed page with an optional next cursor.
    """
    return await load_public_feed(resources, kind, cursor, limit)


@router.get(
    "/following",
    response_model=FeedResponse,
    summary="Read the following feed",
    description="Chronological mixed feed from followed authors; requires a session cookie.",
    tags=["Feeds"],
    responses=documented_responses(401, 503),
)
async def following_feed(
    resources: Resources,
    current_user: CurrentUser,
    kind: FeedKind = "all",
    cursor: str | None = Query(default=None, max_length=2048),
    limit: int = Query(
        default=20,
        ge=1,
        le=50,
        description="Feed page size from 1 to 50; defaults to 20.",
    ),
) -> FeedResponse:
    """Read publications by accounts followed by the current user.

    :param resources: Application-owned database, cache, and storage clients.
    :param current_user: Account resolved from the current session cookie.
    :param kind: Publication type filter: micro_post, article, or all when supported.
    :param cursor: Opaque cursor from the preceding feed page, if any.
    :param limit: Maximum number of entries to return in this page.
    :return: The following feed page with an optional next cursor.
    """
    return await load_following_feed(resources, current_user, kind, cursor, limit)
