"""HTTP adapters for publication operations."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from backend.api import examples
from backend.api.metadata import (
    ArticleId,
    Origin,
    PostId,
    ShareSlug,
    Username,
    documented_responses,
)
from backend.audit.dependencies import Audit
from backend.auth.dependencies import CurrentUser, OptionalUser
from backend.content.models import Article, MicroPost
from backend.content.presenters import article_response, post_response
from backend.content.schemas import (
    ArticleCreate,
    ArticleResponse,
    ArticleScheduleRequest,
    ArticleUpdate,
    MicroPostCreate,
    MicroPostResponse,
)
from backend.content.service import ContentService
from backend.core.resources import Resources

router = APIRouter()


def get_content_service(resources: Resources, audit: Audit) -> ContentService:
    """Create the publication service from request-scoped dependencies.

    :param resources: Application-owned database, cache, and storage clients.
    :param audit: Request metadata attached to audited operations.
    :return: The configured content service.
    """
    return ContentService(resources, audit)


Content = Annotated[ContentService, Depends(get_content_service)]


@router.post(
    "/posts",
    response_model=MicroPostResponse,
    status_code=201,
    summary="Publish a micro-post",
    description="Creates a public post immediately. Text is trimmed and limited to 280 characters.",
    tags=["Micro-posts"],
    responses=documented_responses(
        401,
        403,
        409,
        503,
        examples=[(examples.POST, "New public note")],
        success_status=201,
    ),
)
async def create_micro_post(
    _origin: Origin,
    payload: MicroPostCreate,
    current_user: CurrentUser,
    content: Content,
) -> MicroPostResponse:
    """Publish a micro-post for the authenticated account.

    :param _origin: Validated Origin header required by mutating API operations.
    :param payload: Validated request data for the operation.
    :param current_user: Account resolved from the current session cookie.
    :param content: Publication application service injected for this request.
    :return: The created micro-post response.
    """
    return post_response(await content.create_post(payload, current_user), current_user)


@router.get(
    "/posts/{post_id}",
    response_model=MicroPostResponse,
    summary="Get a micro-post",
    description="Returns a public post; deleted or malformed identifiers return 404.",
    tags=["Micro-posts"],
    responses=documented_responses(404, 503),
)
async def get_micro_post(post_id: PostId, content: Content) -> MicroPostResponse:
    """Read a public, undeleted micro-post and its author.

    :param post_id: MongoDB identifier of the micro-post.
    :param content: Publication application service injected for this request.
    :return: The public micro-post response.
    """
    post, author = await content.get_post(post_id)

    return post_response(post, author)


@router.patch(
    "/posts/{post_id}",
    response_model=MicroPostResponse,
    summary="Edit your micro-post",
    description="Only the author may edit a post. The complete text field is required.",
    tags=["Micro-posts"],
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def update_micro_post(
    _origin: Origin,
    post_id: PostId,
    payload: MicroPostCreate,
    current_user: CurrentUser,
    content: Content,
) -> MicroPostResponse:
    """Replace the authenticated author's micro-post text.

    :param _origin: Validated Origin header required by mutating API operations.
    :param post_id: MongoDB identifier of the micro-post.
    :param payload: Validated request data for the operation.
    :param current_user: Account resolved from the current session cookie.
    :param content: Publication application service injected for this request.
    :return: The updated micro-post response.
    """
    return post_response(await content.edit_post(post_id, payload, current_user), current_user)


@router.delete(
    "/posts/{post_id}",
    status_code=204,
    summary="Delete your micro-post",
    description="Soft-deletes the post; only the author may delete it.",
    tags=["Micro-posts"],
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def delete_micro_post(
    _origin: Origin,
    post_id: PostId,
    current_user: CurrentUser,
    content: Content,
) -> Response:
    """Soft-delete the authenticated author's micro-post.

    :param _origin: Validated Origin header required by mutating API operations.
    :param post_id: MongoDB identifier of the micro-post.
    :param current_user: Account resolved from the current session cookie.
    :param content: Publication application service injected for this request.
    :return: An empty response with status 204.
    """
    await content.delete(MicroPost, post_id, current_user)

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
    content: Content,
) -> Response:
    """Soft-delete the authenticated author's article.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param current_user: Account resolved from the current session cookie.
    :param content: Publication application service injected for this request.
    :return: An empty response with status 204.
    """
    await content.delete(Article, article_id, current_user)

    return Response(status_code=204)


@router.post(
    "/articles",
    response_model=ArticleResponse,
    status_code=201,
    summary="Create an article draft",
    description=("Creates a private-to-author draft. The body must follow the supported TipTap JSON schema."),
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
    content: Content,
) -> ArticleResponse:
    """Create an article draft for the authenticated account.

    :param _origin: Validated Origin header required by mutating API operations.
    :param payload: Validated request data for the operation.
    :param current_user: Account resolved from the current session cookie.
    :param content: Publication application service injected for this request.
    :return: The created article response.
    """
    return article_response(await content.create_article(payload, current_user), current_user)


@router.get(
    "/publications/{username}/{share_slug}",
    response_model=MicroPostResponse | ArticleResponse,
    summary="Read a shared publication",
    description=("Resolves the UUID-safe slug in /@username/slug--share-id and returns the public post or article."),
    tags=["Publications"],
    responses=documented_responses(
        404,
        503,
        examples=[
            (examples.POST_WITH_IMAGES, "Public micro-post"),
            (examples.ARTICLE_PUBLISHED, "Published article"),
        ],
    ),
)
async def get_shared_publication(
    username: Username,
    share_slug: ShareSlug,
    content: Content,
) -> MicroPostResponse | ArticleResponse:
    """Resolve a public publication using its author's handle and share slug.

    :param username: Public profile handle, optionally prefixed with @.
    :param share_slug: Readable share slug ending with the stable publication share ID.
    :param content: Publication application service injected for this request.
    :return: The matching micro-post or published article response.
    """
    publication, author = await content.shared(username, share_slug)

    return (
        post_response(publication, author)
        if isinstance(publication, MicroPost)
        else article_response(publication, author)
    )


@router.get(
    "/me/articles",
    response_model=list[ArticleResponse],
    summary="List your articles",
    description=(
        "Returns your articles. Filter status by all, draft, scheduled, or published; "
        "defaults to all. Unpublished articles are visible only to their author. Offset "
        "defaults to 0; limit defaults to 20 and is capped at 100. Ordering is updated_at and "
        "ID descending."
    ),
    tags=["Articles"],
    responses=documented_responses(401, 503),
)
async def list_my_articles(
    current_user: CurrentUser,
    content: Content,
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
    :param content: Publication application service injected for this request.
    :param article_status: Article status filter, including all for every status.
    :param offset: Number of matching entries to skip before selecting the page.
    :param limit: Maximum number of entries to return in this page.
    :return: The requested page of article responses.
    """
    articles = await content.list_mine(current_user, None if article_status == "all" else article_status, offset, limit)

    return [article_response(article, current_user) for article in articles]


@router.get(
    "/articles/{article_id}",
    response_model=ArticleResponse,
    summary="Get an article",
    description=(
        "Returns the full TipTap body and media URLs. Published articles are public; drafts "
        "and scheduled articles require their author's session. Missing, deleted, "
        "inaccessible, and malformed IDs return 404."
    ),
    tags=["Articles"],
    responses=documented_responses(404, 503),
    openapi_extra={"security": [{}, {"SessionCookie": []}]},
)
async def get_article(article_id: ArticleId, current_user: OptionalUser, content: Content) -> ArticleResponse:
    """Read a visible article, allowing private drafts only for their author.

    :param article_id: MongoDB identifier of the article.
    :param current_user: Account resolved from the session cookie, or None for anonymous
        access.
    :param content: Publication application service injected for this request.
    :return: The article response including its body.
    """
    article, author = await content.get_article(article_id, current_user)

    return article_response(article, author)


@router.patch(
    "/articles/{article_id}",
    response_model=ArticleResponse,
    summary="Edit your article",
    description="Partial update of title, summary, or TipTap JSON body; only the author may edit.",
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
    content: Content,
) -> ArticleResponse:
    """Apply supplied fields to an article owned by the current account.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param payload: Validated request data for the operation.
    :param current_user: Account resolved from the current session cookie.
    :param content: Publication application service injected for this request.
    :return: The updated article response.
    """
    return article_response(await content.edit_article(article_id, payload, current_user), current_user)


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
    content: Content,
) -> ArticleResponse:
    """Publish an owned article immediately.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param current_user: Account resolved from the current session cookie.
    :param content: Publication application service injected for this request.
    :return: The published article response.
    """
    return article_response(await content.transition(article_id, current_user, "published"), current_user)


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
    content: Content,
) -> ArticleResponse:
    """Unpublish an owned article and clear its pending schedule.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param current_user: Account resolved from the current session cookie.
    :param content: Publication application service injected for this request.
    :return: The draft article response.
    """
    return article_response(await content.transition(article_id, current_user, "draft"), current_user)


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
    content: Content,
) -> ArticleResponse:
    """Schedule an owned article for a future publication time.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param payload: Validated request data for the operation.
    :param current_user: Account resolved from the current session cookie.
    :param content: Publication application service injected for this request.
    :return: The scheduled article response.
    """
    return article_response(
        await content.transition(article_id, current_user, "scheduled", payload.publish_at),
        current_user,
    )
