"""Public HTTP adapters for independent profile and mixed-publication search."""

from fastapi import APIRouter, Query

from backend.api.metadata import documented_responses
from backend.core.resources import Resources
from backend.links.presentation import hydrate_publications
from backend.search.query import SearchSort
from backend.search.schemas import SearchPublicationsPage, SearchUsersPage
from backend.search.service import search_publications, search_users

router = APIRouter(prefix="/search", tags=["Search"])
QUERY_DESCRIPTION = (
    "Literal text, up to 200 characters. All words must match; each #hashtag adds a mandatory exact, "
    "case-insensitive filter. Text requires two characters; a one-character hashtag is valid. "
    "No stemming; the last word supports prefixes, and words of four or more characters allow one typo."
)


@router.get(
    "/users", response_model=SearchUsersPage, summary="Search public profiles",
    description=(
        "Search username (optionally prefixed with @), public name, and biography without authentication. "
        "Exact usernames rank first, followed by username prefixes, public names, and biographies. "
        "Hashtags are extracted from public names and biographies. Search indexing is eventually consistent."
    ), responses=documented_responses(422, 503),
)
async def users(
    q: str = Query(min_length=1, max_length=200, description=QUERY_DESCRIPTION, examples=["python"]),
    cursor: str | None = Query(default=None, max_length=8192, description="Continuation from this exact user query."),
    limit: int = Query(default=3, ge=1, le=50, description="Profiles per page; the UI starts with 3 and expands by 10."),
) -> SearchUsersPage:
    """Read matching public profiles without exposing private account fields.

    :param q: Literal words and optional exact hashtag filters.
    :param cursor: User-search continuation, or None for the initial page.
    :param limit: Maximum number of matching profiles to return.
    :return: Public cards with biographies and an optional continuation.
    """
    return await search_users(q, cursor, limit)


@router.get(
    "/publications", response_model=SearchPublicationsPage, summary="Search public publications",
    description=(
        "Mixed full-text search of posts, complete article bodies and titles, replies, and comments. "
        "Repost events do not duplicate originals. Drafts, scheduled, deleted, archived, and inaccessible "
        "discussion content are excluded for every viewer. Visibility is rechecked before pagination; "
        "cards and excerpts use current source data. Indexed matching can lag behind recent edits."
    ), responses=documented_responses(422, 503),
)
async def publications(
    resources: Resources,
    q: str = Query(min_length=1, max_length=200, description=QUERY_DESCRIPTION, examples=["fastapi #python"]),
    sort: SearchSort = Query(
        default="relevance", description="Relevance, or latest publication first; ties use stable IDs.",
    ),
    cursor: str | None = Query(default=None, max_length=8192, description="Continuation bound to this query and sort."),
    limit: int = Query(default=20, ge=1, le=50, description="Visible publication cards per page."),
) -> SearchPublicationsPage:
    """Read a visibility-filtered mixed search page and hydrate its cached link metadata.

    :param resources: Application clients used for batched link presentation.
    :param q: Literal words and optional mandatory hashtags.
    :param sort: Relevance or latest ordering.
    :param cursor: Matching publication-search continuation, or None.
    :param limit: Maximum number of visible publication cards to return.
    :return: Current publication cards, optional passages, and a continuation.
    """
    return await hydrate_publications(resources.redis, await search_publications(q, sort, cursor, limit))
