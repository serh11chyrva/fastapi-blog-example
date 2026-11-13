"""HTTP adapters for micro-post operations."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from backend.api import examples
from backend.api.metadata import Origin, PostId, documented_responses
from backend.audit.dependencies import Audit
from backend.auth.dependencies import CurrentUser, OptionalUser
from backend.core.resources import Resources
from backend.feeds.schemas import AuthorThreadPage
from backend.links.presentation import hydrate_publications
from backend.posts.context import PostContext, post_context
from backend.posts.presenters import post_response
from backend.posts.schemas import MicroPostCreate, MicroPostResponse, PostDraftRequest
from backend.posts.service import PostService
from backend.posts.threads import author_thread_page
from backend.publications.access import publication_is_public
from backend.publications.queries import load_authors

router = APIRouter()


@router.get(
    "/posts/{post_id}/thread", response_model=AuthorThreadPage, tags=["Micro-posts"],
    summary="Read an automatic author thread",
    description="A standalone original and connected same-owner continuations in ascending creation-time and ID order. "
    "Branches through another account are excluded. Deleted connectors retain navigation-only tombstones. "
    "The original is returned separately; limit counts continuations.",
    responses=documented_responses(404, 422, 503), openapi_extra={"security": [{}, {"SessionCookie": []}]},
)
async def get_author_thread(
    post_id: PostId, resources: Resources, current_user: OptionalUser, response: Response,
    cursor: Annotated[str | None, Query(max_length=512, description="Root-bound cursor from the preceding page.")] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="Continuations per page; defaults to 20.")] = 20,
) -> AuthorThreadPage:
    """Read a bounded author-thread page with current visibility checks.

    :param post_id: Standalone original post identifier.
    :param resources: Cache infrastructure for current attachment presentations.
    :param current_user: Optional owner allowed to read archived content.
    :param response: HTTP response receiving a private cache policy.
    :param cursor: Root-bound position from the previous page, or None.
    :param limit: Maximum number of continuations to return.
    :return: Original post and one ascending page of author continuations.
    """
    response.headers["Cache-Control"] = "private, no-store"
    return await hydrate_publications(
        resources.redis, await author_thread_page(post_id, cursor, limit, current_user.id if current_user else None),
    )


@router.get(
    "/posts/{post_id}/context", response_model=PostContext, tags=["Micro-posts"],
    summary="Read a post conversation path",
    description="Selected post, original publication, and all reply ancestors in reading order. "
    "Deleted replies are content-free navigation tombstones. Archived dependencies require their owner's session.",
    responses=documented_responses(404, 503),
    openapi_extra={"security": [{}, {"SessionCookie": []}]},
)
async def get_post_context(
    post_id: PostId, resources: Resources, current_user: OptionalUser, response: Response,
) -> PostContext:
    """Read the authorized path to a live post or deleted reply.

    :param post_id: Selected post or deleted reply identifier.
    :param resources: Application-owned cache used for attachment presentations.
    :param current_user: Optional session granting owner-only archived reads.
    :param response: HTTP response receiving a private cache policy.
    :return: The selected publication and its ordered discussion context.
    """
    response.headers["Cache-Control"] = "private, no-store"
    return await hydrate_publications(
        resources.redis, await post_context(post_id, current_user.id if current_user else None),
    )


def get_posts_service(resources: Resources, audit: Audit) -> PostService:
    """Create the posts service from request-scoped dependencies.

    :param resources: Application-owned database, cache, and storage clients.
    :param audit: Request metadata attached to audited operations.
    :return: The configured posts service.
    """
    return PostService(resources, audit)


Posts = Annotated[PostService, Depends(get_posts_service)]


@router.post(
    "/posts/drafts", response_model=MicroPostResponse, status_code=201, tags=["Micro-posts"],
    summary="Reserve a private post upload target",
    description="Use a fresh UUID key for each compose attempt and retain it on retries. "
    "Upload images to the returned post ID, then PATCH the completed content to publish. "
    "Unpublished targets expire after 24 hours without changes and never appear in public reads.",
    responses=documented_responses(401, 403, 404, 503),
)
async def create_post_draft(
    _origin: Origin, payload: PostDraftRequest, current_user: CurrentUser, posts: Posts,
) -> MicroPostResponse:
    """Create or retrieve the owner's private staging publication.

    Cached link presentations are attached after access checks; missing metadata is queued, not fetched here.

    :param _origin: Validated mutation origin.
    :param payload: Stable client retry key.
    :param current_user: Account owning the staging target.
    :param posts: Request-scoped post service.
    :return: The private target or its already published result.
    """
    return await hydrate_publications(
        posts.resources.redis,
        post_response(await posts.create_draft(payload.key, current_user), [current_user]),
    )


@router.post(
    "/posts",
    response_model=MicroPostResponse,
    status_code=201,
    summary="Publish a micro-post",
    description=(
        "Creates a public post with optional typed attachments. Text is trimmed and limited to 280 characters. "
        "Referenced accounts must exist and attached articles must be published. Video is reserved and rejected."
    ),
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
    posts: Posts,
) -> MicroPostResponse:
    """Publish a micro-post for the authenticated account.

    Cached link presentations are attached after access checks; missing metadata is queued, not fetched here.

    :param _origin: Validated Origin header required by mutating API operations.
    :param payload: Validated request data for the operation.
    :param current_user: Account resolved from the current session cookie.
    :param posts: Posts application service injected for this request.
    :return: The created micro-post response.
    """
    return await hydrate_publications(
        posts.resources.redis,
        post_response(await posts.create_post(payload, current_user), [current_user]),
    )


@router.get(
    "/posts/{post_id}",
    response_model=MicroPostResponse,
    summary="Get a micro-post",
    openapi_extra={"security": [{}, {"SessionCookie": []}]},
    description="Returns a public post, or archived content only for its owner. Inaccessible IDs return 404.",
    tags=["Micro-posts"],
    responses=documented_responses(404, 503),
)
async def get_micro_post(post_id: PostId, posts: Posts, current_user: OptionalUser, response: Response) -> MicroPostResponse:
    """Read a public micro-post or the owner's archived publication.

    Cached link presentations are attached after access checks; missing metadata is queued, not fetched here.

    :param post_id: MongoDB identifier of the micro-post.
    :param posts: Posts application service injected for this request.
    :param current_user: Optional session for owner-only archived reads.
    :param response: HTTP response for the private cache policy.
    :return: The accessible micro-post response.
    """
    response.headers["Cache-Control"] = "private, no-store"
    post, authors = await posts.get_post(post_id, current_user)

    result = post_response(post, authors)
    if post.reply is not None:
        result.read_only = not await publication_is_public("micro_post", str(post.id))
    return await hydrate_publications(posts.resources.redis, result)


@router.patch(
    "/posts/{post_id}",
    response_model=MicroPostResponse,
    summary="Edit your micro-post",
    description=(
        "Only the owner may edit a post. Omitted text is preserved; supplied attachments replace descriptors. "
        "Text may be empty when an attachment remains. retain_image_urls removes images; image_draft_id replaces a gallery. expected_updated_at rejects stale edits."
    ),
    tags=["Micro-posts"],
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def update_micro_post(
    _origin: Origin,
    post_id: PostId,
    payload: MicroPostCreate,
    current_user: CurrentUser,
    posts: Posts,
) -> MicroPostResponse:
    """Replace the owner's post text and optionally its typed attachments.

    Cached link presentations are attached after access checks; missing metadata is queued, not fetched here.

    :param _origin: Validated Origin header required by mutating API operations.
    :param post_id: MongoDB identifier of the micro-post.
    :param payload: Validated request data for the operation.
    :param current_user: Account resolved from the current session cookie.
    :param posts: Posts application service injected for this request.
    :return: The updated micro-post response.
    """
    post = await posts.edit_post(post_id, payload, current_user)

    return await hydrate_publications(
        posts.resources.redis,
        post_response(post, await load_authors(post.author_ids)),
    )


@router.delete(
    "/posts/{post_id}",
    status_code=204,
    summary="Delete your micro-post",
    description="Soft-deletes the post; only the owner may delete it.",
    tags=["Micro-posts"],
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def delete_micro_post(
    _origin: Origin,
    post_id: PostId,
    current_user: CurrentUser,
    posts: Posts,
) -> Response:
    """Soft-delete the authenticated author's micro-post.

    :param _origin: Validated Origin header required by mutating API operations.
    :param post_id: MongoDB identifier of the micro-post.
    :param current_user: Account resolved from the current session cookie.
    :param posts: Posts application service injected for this request.
    :return: An empty response with status 204.
    """
    await posts.delete(post_id, current_user)

    return Response(status_code=204)
