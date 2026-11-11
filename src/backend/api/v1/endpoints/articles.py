"""HTTP adapters for article operations."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from backend.api import examples
from backend.api.metadata import ArticleId, Origin, documented_responses
from backend.articles.presenters import article_response
from backend.articles.schemas import ArticleCreate, ArticleResponse, ArticleScheduleRequest, ArticleUpdate
from backend.articles.service import ArticleService
from backend.audit.dependencies import Audit
from backend.auth.dependencies import CurrentUser, OptionalUser
from backend.core.resources import Resources
from backend.publications.queries import load_authors

router = APIRouter()


def get_articles_service(resources: Resources, audit: Audit) -> ArticleService:
    """Create the articles service from request-scoped dependencies.

    :param resources: Application-owned database, cache, and storage clients.
    :param audit: Request metadata attached to audited operations.
    :return: The configured articles service.
    """
    return ArticleService(resources, audit)


Articles = Annotated[ArticleService, Depends(get_articles_service)]


@router.delete(
    "/articles/{article_id}/cover", status_code=204, summary="Remove your article cover",
    description="Detach the current cover and queue storage cleanup. Repeating the request is safe.",
    tags=["Articles"], responses=documented_responses(401, 403, 404, 409, 503),
)
async def remove_article_cover(
    _origin: Origin, article_id: ArticleId, current_user: CurrentUser, articles: Articles,
) -> Response:
    """Remove a cover from the owner's article.

    :param _origin: Required same-origin mutation header.
    :param article_id: Owned article identifier.
    :param current_user: Authenticated article owner.
    :param articles: Request-scoped article service.
    :return: Empty response after the cover is detached.
    """
    await articles.remove_cover(article_id, current_user)

    return Response(status_code=204)


@router.delete(
    "/articles/{article_id}",
    status_code=204,
    summary="Delete an article",
    description="Soft-deletes your draft, scheduled article, or publication.",
    tags=["Articles"],
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def delete_article(
    _origin: Origin,
    article_id: ArticleId,
    current_user: CurrentUser,
    articles: Articles,
) -> Response:
    """Soft-delete the authenticated author's article.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param current_user: Account resolved from the current session cookie.
    :param articles: Articles application service injected for this request.
    :return: An empty response with status 204.
    """
    await articles.delete(article_id, current_user)

    return Response(status_code=204)


@router.post(
    "/articles",
    response_model=ArticleResponse,
    status_code=201,
    summary="Create an article draft",
    description=(
        "Creates a private-to-owner draft with optional typed attachments. TipTap supports inline mentions and "
        "hashtags and block attachment descriptors. Mentioned accounts must exist; referenced articles must be published. "
        "Video descriptors are reserved and rejected."
    ),
    tags=["Articles"],
    responses=documented_responses(
        401,
        403,
        409,
        503,
        examples=[(examples.ARTICLE, "New private draft")],
        success_status=201,
    ),
)
async def create_article(
    _origin: Origin,
    payload: ArticleCreate,
    current_user: CurrentUser,
    articles: Articles,
) -> ArticleResponse:
    """Create an article draft for the authenticated account.

    :param _origin: Validated Origin header required by mutating API operations.
    :param payload: Validated request data for the operation.
    :param current_user: Account resolved from the current session cookie.
    :param articles: Articles application service injected for this request.
    :return: The created article response.
    """
    return article_response(await articles.create_article(payload, current_user), [current_user])


@router.get(
    "/me/articles",
    response_model=list[ArticleResponse],
    summary="List your articles",
    description=(
        "Returns your articles. Filter status by all, draft, scheduled, or published; "
        "defaults to all. Unpublished articles are visible only to their owner. Offset "
        "defaults to 0; limit defaults to 20 and is capped at 100. Ordering is updated_at and "
        "ID descending."
    ),
    tags=["Articles"],
    responses=documented_responses(401, 503),
)
async def list_my_articles(
    current_user: CurrentUser,
    articles: Articles,
    article_status: Literal["all", "draft", "scheduled", "published"] = Query(default="all", alias="status"),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip; refresh from zero after concurrent list changes.",
    ),
    limit: int = Query(default=20, ge=1, le=100, description="Page size from 1 to 100; defaults to 20."),
) -> list[ArticleResponse]:
    """List the authenticated author's articles with optional status filtering.

    :param current_user: Account resolved from the current session cookie.
    :param articles: Articles application service injected for this request.
    :param article_status: Article status filter, including all for every status.
    :param offset: Number of matching entries to skip before selecting the page.
    :param limit: Maximum number of entries to return in this page.
    :return: The requested page of article responses.
    """
    items = await articles.list_mine(current_user, None if article_status == "all" else article_status, offset, limit)

    return [article_response(article, authors) for article, authors in items]


@router.get(
    "/articles/{article_id}",
    response_model=ArticleResponse,
    summary="Get an article",
    description=(
        "Returns the full TipTap body and media URLs. Published articles are public; drafts "
        "and scheduled articles require their owner's session. Missing, deleted, "
        "inaccessible, and malformed IDs return 404."
    ),
    tags=["Articles"],
    responses=documented_responses(404, 503),
    openapi_extra={"security": [{}, {"SessionCookie": []}]},
)
async def get_article(article_id: ArticleId, current_user: OptionalUser, articles: Articles) -> ArticleResponse:
    """Read a visible article, allowing private drafts only for their owner.

    :param article_id: MongoDB identifier of the article.
    :param current_user: Account resolved from the session cookie, or None for anonymous
        access.
    :param articles: Articles application service injected for this request.
    :return: The article response including its body.
    """
    article, authors = await articles.get_article(article_id, current_user)

    return article_response(article, authors)


@router.patch(
    "/articles/{article_id}",
    response_model=ArticleResponse,
    summary="Edit your article",
    description=(
        "Summary is generated from the first 280 characters of body text. Partial update of title, TipTap JSON body, or typed attachments; only the owner may edit. "
        "Omitted or null attachments are preserved; [] clears explicit descriptors. "
        "References are checked in the write transaction."
    ),
    tags=["Articles"],
    responses=documented_responses(
        401,
        403,
        404,
        409,
        503,
        examples=[(examples.ARTICLE_UPDATED, "Updated private article")],
    ),
)
async def update_article(
    _origin: Origin,
    article_id: ArticleId,
    payload: ArticleUpdate,
    current_user: CurrentUser,
    articles: Articles,
) -> ArticleResponse:
    """Apply supplied fields to an article owned by the current account.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param payload: Validated request data for the operation.
    :param current_user: Account resolved from the current session cookie.
    :param articles: Articles application service injected for this request.
    :return: The updated article response.
    """
    article = await articles.edit_article(article_id, payload, current_user)

    return article_response(article, await load_authors(article.author_ids))


@router.post(
    "/articles/{article_id}/publish",
    response_model=ArticleResponse,
    summary="Publish an article now",
    description=(
        "Makes your draft or scheduled article public immediately, assigns its publication "
        "timestamp, and clears the schedule. Publishing an already published article leaves "
        "its timestamp unchanged."
    ),
    tags=["Articles"],
    responses=documented_responses(
        401,
        403,
        404,
        409,
        503,
        examples=[
            (
                examples.ARTICLE_PUBLISHED | {"thumbnail_url": None},
                "Article published immediately",
            )
        ],
    ),
)
async def publish_article(
    _origin: Origin,
    article_id: ArticleId,
    current_user: CurrentUser,
    articles: Articles,
) -> ArticleResponse:
    """Publish an owned article immediately.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param current_user: Account resolved from the current session cookie.
    :param articles: Articles application service injected for this request.
    :return: The published article response.
    """
    article = await articles.transition(article_id, current_user, "published")

    return article_response(article, await load_authors(article.author_ids))


@router.post(
    "/articles/{article_id}/draft",
    response_model=ArticleResponse,
    summary="Return an article to draft",
    description="Unpublishes or unschedules your article and makes it private to you.",
    tags=["Articles"],
    responses=documented_responses(
        401,
        403,
        404,
        409,
        503,
        examples=[(examples.ARTICLE, "Private draft with no schedule")],
    ),
)
async def return_article_to_draft(
    _origin: Origin,
    article_id: ArticleId,
    current_user: CurrentUser,
    articles: Articles,
) -> ArticleResponse:
    """Unpublish an owned article and clear its pending schedule.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param current_user: Account resolved from the current session cookie.
    :param articles: Articles application service injected for this request.
    :return: The draft article response.
    """
    article = await articles.transition(article_id, current_user, "draft")

    return article_response(article, await load_authors(article.author_ids))


@router.post(
    "/articles/{article_id}/schedule",
    response_model=ArticleResponse,
    summary="Schedule an article",
    description=("Sets a future timezone-aware publication time; the background worker publishes it automatically."),
    tags=["Articles"],
    responses=documented_responses(
        401,
        403,
        404,
        409,
        503,
        examples=[(examples.ARTICLE_SCHEDULED, "Article awaiting scheduled publication")],
    ),
)
async def schedule_article(
    _origin: Origin,
    article_id: ArticleId,
    payload: ArticleScheduleRequest,
    current_user: CurrentUser,
    articles: Articles,
) -> ArticleResponse:
    """Schedule an owned article for a future publication time.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param payload: Validated request data for the operation.
    :param current_user: Account resolved from the current session cookie.
    :param articles: Articles application service injected for this request.
    :return: The scheduled article response.
    """
    article = await articles.transition(article_id, current_user, "scheduled", payload.publish_at)

    return article_response(article, await load_authors(article.author_ids))
