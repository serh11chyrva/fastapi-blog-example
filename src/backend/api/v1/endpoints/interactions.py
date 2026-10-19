"""HTTP endpoints for publication interaction state and relationship lists."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Response

from backend.api.metadata import ArticleId, Origin, PostId, Username, documented_responses
from backend.audit.dependencies import Audit
from backend.auth.dependencies import CurrentUser, OptionalUser
from backend.core.resources import Resources
from backend.feeds.schemas import RepostPage
from backend.interactions.schemas import InteractionSummary, SavedPage
from backend.interactions.service import InteractionService

router = APIRouter(tags=["Interactions"])


def get_interactions_service(resources: Resources, audit: Audit) -> InteractionService:
    """Create the interaction service for this request.

    :param resources: Application-owned infrastructure clients.
    :param audit: Request metadata for transactional audit events.
    :return: The configured interaction service.
    """
    return InteractionService(resources, audit)


Interactions = Annotated[InteractionService, Depends(get_interactions_service)]
ListCursor = Annotated[str | None, Query(max_length=24, description="Last scanned relationship ID; pass unchanged.")]
ListLimit = Annotated[int, Query(ge=1, le=50, description="Relationships to scan, from 1 to 50; defaults to 20.")]


@router.get(
    "/posts/{post_id}/interactions", response_model=InteractionSummary,
    summary="Read post counts and your interaction state",
    description="Public live counts and optional viewer flags. Private save totals are never exposed. "
    "Only public originals are available, including for their owner. Personalized responses are not cached.",
    responses=documented_responses(404, 503),
    openapi_extra={"security": [{}, {"SessionCookie": []}]},
)
async def post_interactions(
    post_id: PostId, current_user: OptionalUser, interactions: Interactions, response: Response,
) -> InteractionSummary:
    """Read public engagement and the optional current account's flags.

    :param post_id: Original post identifier.
    :param current_user: Authenticated viewer, or None for anonymous false flags.
    :param interactions: Request-scoped interaction service.
    :param response: HTTP response receiving private no-store cache headers.
    :return: Public counts and viewer-specific interaction state.
    """
    response.headers["Cache-Control"] = "private, no-store"

    return await interactions.summary("micro_post", post_id, current_user)


@router.put(
    "/posts/{post_id}/like", status_code=204,
    summary="Add your post like",
    description="Idempotent desired state; no request body. Creation requires a public original. "
    "Removal also works after deletion or unpublishing. "
    "Concurrent changes may return 409; reload before retrying.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def put_post_like(
    _origin: Origin, post_id: PostId, current_user: CurrentUser, interactions: Interactions,
) -> Response:
    """Add the current account's like without toggling its existing state.

    :param _origin: Required same-origin mutation header.
    :param post_id: Original post identifier.
    :param current_user: Account owning the interaction.
    :param interactions: Request-scoped interaction service.
    :return: An empty 204 response after the desired state is committed.
    """
    await interactions.set_state("micro_post", post_id, "like", True, current_user)

    return Response(status_code=204)


@router.delete(
    "/posts/{post_id}/like", status_code=204,
    summary="Remove your post like",
    description="Idempotent desired state; no request body. Creation requires a public original. "
    "Removal also works after deletion or unpublishing. "
    "Concurrent changes may return 409; reload before retrying.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def delete_post_like(
    _origin: Origin, post_id: PostId, current_user: CurrentUser, interactions: Interactions,
) -> Response:
    """Remove the current account's like without toggling its existing state.

    :param _origin: Required same-origin mutation header.
    :param post_id: Original post identifier.
    :param current_user: Account owning the interaction.
    :param interactions: Request-scoped interaction service.
    :return: An empty 204 response after the desired state is committed.
    """
    await interactions.set_state("micro_post", post_id, "like", False, current_user)

    return Response(status_code=204)


@router.put(
    "/posts/{post_id}/save", status_code=204,
    summary="Add your post save",
    description="Idempotent desired state; no request body. Creation requires a public original. "
    "Removal also works after deletion or unpublishing. "
    "Concurrent changes may return 409; reload before retrying.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def put_post_save(
    _origin: Origin, post_id: PostId, current_user: CurrentUser, interactions: Interactions,
) -> Response:
    """Add the current account's save without toggling its existing state.

    :param _origin: Required same-origin mutation header.
    :param post_id: Original post identifier.
    :param current_user: Account owning the interaction.
    :param interactions: Request-scoped interaction service.
    :return: An empty 204 response after the desired state is committed.
    """
    await interactions.set_state("micro_post", post_id, "save", True, current_user)

    return Response(status_code=204)


@router.delete(
    "/posts/{post_id}/save", status_code=204,
    summary="Remove your post save",
    description="Idempotent desired state; no request body. Creation requires a public original. "
    "Removal also works after deletion or unpublishing. "
    "Concurrent changes may return 409; reload before retrying.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def delete_post_save(
    _origin: Origin, post_id: PostId, current_user: CurrentUser, interactions: Interactions,
) -> Response:
    """Remove the current account's save without toggling its existing state.

    :param _origin: Required same-origin mutation header.
    :param post_id: Original post identifier.
    :param current_user: Account owning the interaction.
    :param interactions: Request-scoped interaction service.
    :return: An empty 204 response after the desired state is committed.
    """
    await interactions.set_state("micro_post", post_id, "save", False, current_user)

    return Response(status_code=204)


@router.put(
    "/posts/{post_id}/repost", status_code=204,
    summary="Add your post repost",
    description="Idempotent desired state; no request body. Creation requires a public original. "
    "Removal also works after deletion or unpublishing. "
    "Concurrent changes may return 409; reload before retrying.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def put_post_repost(
    _origin: Origin, post_id: PostId, current_user: CurrentUser, interactions: Interactions,
) -> Response:
    """Add the current account's repost without toggling its existing state.

    :param _origin: Required same-origin mutation header.
    :param post_id: Original post identifier.
    :param current_user: Account owning the interaction.
    :param interactions: Request-scoped interaction service.
    :return: An empty 204 response after the desired state is committed.
    """
    await interactions.set_state("micro_post", post_id, "repost", True, current_user)

    return Response(status_code=204)


@router.delete(
    "/posts/{post_id}/repost", status_code=204,
    summary="Remove your post repost",
    description="Idempotent desired state; no request body. Creation requires a public original. "
    "Removal also works after deletion or unpublishing. "
    "Concurrent changes may return 409; reload before retrying.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def delete_post_repost(
    _origin: Origin, post_id: PostId, current_user: CurrentUser, interactions: Interactions,
) -> Response:
    """Remove the current account's repost without toggling its existing state.

    :param _origin: Required same-origin mutation header.
    :param post_id: Original post identifier.
    :param current_user: Account owning the interaction.
    :param interactions: Request-scoped interaction service.
    :return: An empty 204 response after the desired state is committed.
    """
    await interactions.set_state("micro_post", post_id, "repost", False, current_user)

    return Response(status_code=204)


@router.get(
    "/articles/{article_id}/interactions", response_model=InteractionSummary,
    summary="Read article counts and your interaction state",
    description="Public live counts and optional viewer flags. Private save totals are never exposed. "
    "Only public originals are available, including for their owner. Personalized responses are not cached.",
    responses=documented_responses(404, 503),
    openapi_extra={"security": [{}, {"SessionCookie": []}]},
)
async def article_interactions(
    article_id: ArticleId, current_user: OptionalUser, interactions: Interactions, response: Response,
) -> InteractionSummary:
    """Read public engagement and the optional current account's flags.

    :param article_id: Original article identifier.
    :param current_user: Authenticated viewer, or None for anonymous false flags.
    :param interactions: Request-scoped interaction service.
    :param response: HTTP response receiving private no-store cache headers.
    :return: Public counts and viewer-specific interaction state.
    """
    response.headers["Cache-Control"] = "private, no-store"

    return await interactions.summary("article", article_id, current_user)


@router.put(
    "/articles/{article_id}/like", status_code=204,
    summary="Add your article like",
    description="Idempotent desired state; no request body. Creation requires a public original. "
    "Removal also works after deletion or unpublishing. "
    "Concurrent changes may return 409; reload before retrying.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def put_article_like(
    _origin: Origin, article_id: ArticleId, current_user: CurrentUser, interactions: Interactions,
) -> Response:
    """Add the current account's like without toggling its existing state.

    :param _origin: Required same-origin mutation header.
    :param article_id: Original article identifier.
    :param current_user: Account owning the interaction.
    :param interactions: Request-scoped interaction service.
    :return: An empty 204 response after the desired state is committed.
    """
    await interactions.set_state("article", article_id, "like", True, current_user)

    return Response(status_code=204)


@router.delete(
    "/articles/{article_id}/like", status_code=204,
    summary="Remove your article like",
    description="Idempotent desired state; no request body. Creation requires a public original. "
    "Removal also works after deletion or unpublishing. "
    "Concurrent changes may return 409; reload before retrying.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def delete_article_like(
    _origin: Origin, article_id: ArticleId, current_user: CurrentUser, interactions: Interactions,
) -> Response:
    """Remove the current account's like without toggling its existing state.

    :param _origin: Required same-origin mutation header.
    :param article_id: Original article identifier.
    :param current_user: Account owning the interaction.
    :param interactions: Request-scoped interaction service.
    :return: An empty 204 response after the desired state is committed.
    """
    await interactions.set_state("article", article_id, "like", False, current_user)

    return Response(status_code=204)


@router.put(
    "/articles/{article_id}/save", status_code=204,
    summary="Add your article save",
    description="Idempotent desired state; no request body. Creation requires a public original. "
    "Removal also works after deletion or unpublishing. "
    "Concurrent changes may return 409; reload before retrying.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def put_article_save(
    _origin: Origin, article_id: ArticleId, current_user: CurrentUser, interactions: Interactions,
) -> Response:
    """Add the current account's save without toggling its existing state.

    :param _origin: Required same-origin mutation header.
    :param article_id: Original article identifier.
    :param current_user: Account owning the interaction.
    :param interactions: Request-scoped interaction service.
    :return: An empty 204 response after the desired state is committed.
    """
    await interactions.set_state("article", article_id, "save", True, current_user)

    return Response(status_code=204)


@router.delete(
    "/articles/{article_id}/save", status_code=204,
    summary="Remove your article save",
    description="Idempotent desired state; no request body. Creation requires a public original. "
    "Removal also works after deletion or unpublishing. "
    "Concurrent changes may return 409; reload before retrying.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def delete_article_save(
    _origin: Origin, article_id: ArticleId, current_user: CurrentUser, interactions: Interactions,
) -> Response:
    """Remove the current account's save without toggling its existing state.

    :param _origin: Required same-origin mutation header.
    :param article_id: Original article identifier.
    :param current_user: Account owning the interaction.
    :param interactions: Request-scoped interaction service.
    :return: An empty 204 response after the desired state is committed.
    """
    await interactions.set_state("article", article_id, "save", False, current_user)

    return Response(status_code=204)


@router.get(
    "/me/saved", response_model=SavedPage, summary="List your privately saved publications",
    description="Only the current account's saves, newest relationship ID first. Unavailable originals are filtered. "
    "An empty page can have a next cursor; continue until next_cursor is null. Responses are never publicly cached.",
    responses=documented_responses(401, 404, 503),
)
async def saved_publications(
    current_user: CurrentUser, interactions: Interactions, response: Response,
    cursor: ListCursor = None, limit: ListLimit = 20,
) -> SavedPage:
    """Read the authenticated account's private saved-publication page.

    :param current_user: Account whose saves are requested; no other account ID is accepted.
    :param interactions: Request-scoped interaction service.
    :param response: HTTP response receiving private no-store cache headers.
    :param cursor: Last scanned relationship identifier, or None for the first page.
    :param limit: Maximum number of relationships to scan.
    :return: Currently public saved originals and a continuation cursor.
    """
    response.headers["Cache-Control"] = "private, no-store"

    return cast(SavedPage, await interactions.list_entries(current_user, "save", cursor, limit))


@router.get(
    "/profiles/{username}/reposts", response_model=RepostPage, summary="List an account's public post reposts",
    description="Original posts wrapped with the reposter and repost time. Deleted originals are filtered. "
    "Ordered by relationship ID descending; continue while next_cursor is non-null, even after an empty page.",
    responses=documented_responses(404, 503),
)
async def profile_reposts(
    username: Username, interactions: Interactions, cursor: ListCursor = None, limit: ListLimit = 20,
) -> RepostPage:
    """Read public repost history without exposing likes or private saves.

    :param username: Public account handle, optionally prefixed with @.
    :param interactions: Request-scoped interaction service.
    :param cursor: Last scanned repost relationship identifier.
    :param limit: Maximum number of relationships to scan.
    :return: Public repost events and a continuation cursor.
    """
    return await interactions.profile_reposts(username, cursor, limit)
