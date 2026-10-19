"""HTTP adapters for micro-post operations."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from backend.api import examples
from backend.api.metadata import Origin, PostId, documented_responses
from backend.audit.dependencies import Audit
from backend.auth.dependencies import CurrentUser
from backend.core.resources import Resources
from backend.posts.presenters import post_response
from backend.posts.schemas import MicroPostCreate, MicroPostResponse
from backend.posts.service import PostService
from backend.publications.queries import load_authors

router = APIRouter()


def get_posts_service(resources: Resources, audit: Audit) -> PostService:
    """Create the posts service from request-scoped dependencies.

    :param resources: Application-owned database, cache, and storage clients.
    :param audit: Request metadata attached to audited operations.
    :return: The configured posts service.
    """
    return PostService(resources, audit)


Posts = Annotated[PostService, Depends(get_posts_service)]


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

    :param _origin: Validated Origin header required by mutating API operations.
    :param payload: Validated request data for the operation.
    :param current_user: Account resolved from the current session cookie.
    :param posts: Posts application service injected for this request.
    :return: The created micro-post response.
    """
    return post_response(await posts.create_post(payload, current_user), [current_user])


@router.get(
    "/posts/{post_id}",
    response_model=MicroPostResponse,
    summary="Get a micro-post",
    description="Returns a public post; deleted or malformed identifiers return 404.",
    tags=["Micro-posts"],
    responses=documented_responses(404, 503),
)
async def get_micro_post(post_id: PostId, posts: Posts) -> MicroPostResponse:
    """Read a public, undeleted micro-post and its authors.

    :param post_id: MongoDB identifier of the micro-post.
    :param posts: Posts application service injected for this request.
    :return: The public micro-post response.
    """
    post, authors = await posts.get_post(post_id)

    return post_response(post, authors)


@router.patch(
    "/posts/{post_id}",
    response_model=MicroPostResponse,
    summary="Edit your micro-post",
    description=(
        "Only the owner may edit a post. Text is required; supplied attachments replace explicit descriptors. "
        "Omitted attachments are preserved. Image uploads remain managed by the upload endpoints."
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

    :param _origin: Validated Origin header required by mutating API operations.
    :param post_id: MongoDB identifier of the micro-post.
    :param payload: Validated request data for the operation.
    :param current_user: Account resolved from the current session cookie.
    :param posts: Posts application service injected for this request.
    :return: The updated micro-post response.
    """
    post = await posts.edit_post(post_id, payload, current_user)

    return post_response(post, await load_authors(post.author_ids))


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
