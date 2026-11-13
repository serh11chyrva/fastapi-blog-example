"""HTTP query parameters for chronological feeds."""

from fastapi import APIRouter, Query

from backend.api.metadata import documented_responses
from backend.auth.dependencies import CurrentUser
from backend.core.resources import Resources
from backend.feeds.repository import FeedKind
from backend.feeds.schemas import FeedResponse
from backend.feeds.service import load_following_feed, load_public_feed
from backend.links.presentation import hydrate_publications

router = APIRouter(prefix="/feeds")


@router.get(
    "/public",
    response_model=FeedResponse,
    summary="Read the public feed",
    description=(
        "Chronological mixed feed of public posts, published articles, and post repost events. "
        "kind=micro_post includes reposts; kind=article excludes them. Reposts retain their original post and author. "
        "Standalone post cards include up to two connected same-owner continuations in thread_preview; "
        "their chronological position remains the original publication time."
    ),
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

    Cached link presentations are attached after access checks; missing metadata is queued, not fetched here.

    :param resources: Application-owned database, cache, and storage clients.
    :param kind: Publication type filter: micro_post, article, or all when supported.
    :param cursor: Opaque cursor from the preceding feed page, if any.
    :param limit: Maximum number of entries to return in this page.
    :return: The public feed page with an optional next cursor.
    """
    return await hydrate_publications(
        resources.redis,
        await load_public_feed(resources, kind, cursor, limit),
    )


@router.get(
    "/following",
    response_model=FeedResponse,
    summary="Read the following feed",
    description=(
        "Chronological public publications by followed authors and reposts by followed accounts. "
        "A repost can introduce a post by an unfollowed author. kind=micro_post includes reposts. "
        "Original posts include automatic author-thread previews without changing their publication time. "
        "Requires a session cookie."
    ),
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

    Cached link presentations are attached after access checks; missing metadata is queued, not fetched here.

    :param resources: Application-owned database, cache, and storage clients.
    :param current_user: Account resolved from the current session cookie.
    :param kind: Publication type filter: micro_post, article, or all when supported.
    :param cursor: Opaque cursor from the preceding feed page, if any.
    :param limit: Maximum number of entries to return in this page.
    :return: The following feed page with an optional next cursor.
    """
    return await hydrate_publications(
        resources.redis,
        await load_following_feed(resources, current_user, kind, cursor, limit),
    )
