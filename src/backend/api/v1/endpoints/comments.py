"""HTTP endpoints for threaded post replies and flat article comments."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Path, Query, Response

from backend.api.metadata import ArticleId, Origin, PostId, documented_responses
from backend.audit.dependencies import Audit
from backend.auth.dependencies import CurrentUser
from backend.comments.presenters import comment_responses
from backend.comments.schemas import (
    ArticleCommentPage,
    ArticleCommentResponse,
    CommentText,
    PostReplyCreate,
    PostReplyPage,
    PostReplyResponse,
)
from backend.comments.service import CommentService
from backend.core.resources import Resources

router = APIRouter(tags=["Comments"])
CommentId = Annotated[str, Path(description="Comment or reply ObjectId within this publication.")]
CommentCursor = Annotated[str | None, Query(max_length=24, description="Last comment ID from the preceding page.")]
CommentLimit = Annotated[int, Query(ge=1, le=50, description="Page size from 1 to 50; defaults to 20.")]


def get_comments_service(resources: Resources, audit: Audit) -> CommentService:
    """Create the discussion service for this request.

    :param resources: Application-owned infrastructure clients.
    :param audit: Request metadata for transactional audit events.
    :return: The configured discussion service.
    """
    return CommentService(resources, audit)


Comments = Annotated[CommentService, Depends(get_comments_service)]


@router.get(
    "/posts/{post_id}/replies", response_model=PostReplyPage,
    summary="List post replies",
    description="Read roots by default, or direct children of parent_id; descendants load level by level. "
    "Oldest ObjectId first, with tombstones retained. Deleted or unpublished originals return 404.",
    responses=documented_responses(404, 503),
)
async def list_post_replies(
    post_id: PostId, comments: Comments,
    cursor: CommentCursor = None, limit: CommentLimit = 20,
    parent_id: Annotated[str | None, Query(max_length=24, description="Parent reply; omit for root replies.")] = None,
) -> PostReplyPage:
    """Read a bounded direct-child level of the post thread.

    :param post_id: Public containing post identifier.
    :param comments: Request-scoped discussion service.
    :param cursor: Last returned comment ID, or None for the first page.
    :param limit: Maximum number of entries to return.
    :param parent_id: Parent reply ID, including a tombstone, or None to read roots.
    :return: Discussion entries and an optional next cursor.
    """
    return cast(PostReplyPage, await comments.page("micro_post", post_id, parent_id, cursor, limit))


@router.post(
    "/posts/{post_id}/replies", response_model=PostReplyResponse, status_code=201,
    summary="Add a post reply",
    description="Plain text, trimmed and nonblank, up to 5,000 characters. "
    "Optional parent_id must identify a live reply in this exact post; nesting depth is not capped.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def create_post_comment(
    _origin: Origin, post_id: PostId, payload: PostReplyCreate,
    current_user: CurrentUser, comments: Comments,
) -> PostReplyResponse:
    """Add an authored discussion entry to a public post.

    :param _origin: Required same-origin mutation header.
    :param post_id: Public containing post identifier.
    :param payload: Plain text and optional parent reply.
    :param current_user: Authenticated comment author.
    :param comments: Request-scoped discussion service.
    :return: The committed comment with public author data.
    """
    item = await comments.create("micro_post", post_id, payload, current_user, payload.parent_id)

    return cast(PostReplyResponse, (await comment_responses([item]))[0])


@router.get(
    "/posts/{post_id}/replies/{comment_id}", response_model=PostReplyResponse,
    summary="Read a post discussion entry",
    description="Read a scoped comment, including deleted tombstones; inaccessible originals return 404.",
    responses=documented_responses(404, 503),
)
async def get_post_comment(
    post_id: PostId, comment_id: CommentId, comments: Comments,
) -> PostReplyResponse:
    """Read one comment after checking containing-publication visibility.

    :param post_id: Public containing post identifier.
    :param comment_id: Comment or reply identifier within this publication.
    :param comments: Request-scoped discussion service.
    :return: A live entry or its deleted tombstone.
    """
    item = await comments.get("micro_post", post_id, comment_id)

    return cast(PostReplyResponse, (await comment_responses([item]))[0])


@router.patch(
    "/posts/{post_id}/replies/{comment_id}", response_model=PostReplyResponse,
    summary="Edit your post discussion entry",
    description="Only the comment author may replace live text. Thread positions and parent IDs cannot be changed. "
    "A publication owner has no editing rights over other accounts' comments.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def edit_post_comment(
    _origin: Origin, post_id: PostId, comment_id: CommentId, payload: CommentText,
    current_user: CurrentUser, comments: Comments,
) -> PostReplyResponse:
    """Replace owned comment text without moving its discussion position.

    :param _origin: Required same-origin mutation header.
    :param post_id: Public containing post identifier.
    :param comment_id: Scoped comment or reply identifier.
    :param payload: Replacement plain text; extra fields are rejected.
    :param current_user: Authenticated account owning this comment.
    :param comments: Request-scoped discussion service.
    :return: The updated entry with its current public author card.
    """
    item = await comments.change("micro_post", post_id, comment_id, current_user, payload)

    return cast(PostReplyResponse, (await comment_responses([item]))[0])


@router.delete(
    "/posts/{post_id}/replies/{comment_id}", status_code=204,
    summary="Delete your post discussion entry",
    description="Only the comment author may erase text. Returns a tombstone on subsequent reads, "
    "preserving child navigation. Repeated deletion is idempotent; inaccessible originals return 404.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def delete_post_comment(
    _origin: Origin, post_id: PostId, comment_id: CommentId,
    current_user: CurrentUser, comments: Comments,
) -> Response:
    """Erase owned content while retaining discussion identifiers and positions.

    :param _origin: Required same-origin mutation header.
    :param post_id: Public containing post identifier.
    :param comment_id: Scoped comment or reply identifier.
    :param current_user: Authenticated account owning this comment.
    :param comments: Request-scoped discussion service.
    :return: An empty 204 response after the deletion commits.
    """
    await comments.change("micro_post", post_id, comment_id, current_user, None)

    return Response(status_code=204)


@router.get(
    "/articles/{article_id}/comments", response_model=ArticleCommentPage,
    summary="List article comments",
    description="Read a flat discussion; parent IDs and nesting are not supported. "
    "Oldest ObjectId first, with tombstones retained. Deleted or unpublished originals return 404.",
    responses=documented_responses(404, 503),
)
async def list_article_comments(
    article_id: ArticleId, comments: Comments,
    cursor: CommentCursor = None, limit: CommentLimit = 20,
) -> ArticleCommentPage:
    """Read a bounded flat article discussion page.

    :param article_id: Public containing article identifier.
    :param comments: Request-scoped discussion service.
    :param cursor: Last returned comment ID, or None for the first page.
    :param limit: Maximum number of entries to return.
    :return: Discussion entries and an optional next cursor.
    """
    return cast(ArticleCommentPage, await comments.page("article", article_id, None, cursor, limit))


@router.post(
    "/articles/{article_id}/comments", response_model=ArticleCommentResponse, status_code=201,
    summary="Add an article comment",
    description="Plain text, trimmed and nonblank, up to 5,000 characters. "
    "Article comments are strictly flat; extra fields including parent_id return 422.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def create_article_comment(
    _origin: Origin, article_id: ArticleId, payload: CommentText,
    current_user: CurrentUser, comments: Comments,
) -> ArticleCommentResponse:
    """Add an authored discussion entry to a public article.

    :param _origin: Required same-origin mutation header.
    :param article_id: Public containing article identifier.
    :param payload: Plain text without nesting fields.
    :param current_user: Authenticated comment author.
    :param comments: Request-scoped discussion service.
    :return: The committed comment with public author data.
    """
    item = await comments.create("article", article_id, payload, current_user)

    return cast(ArticleCommentResponse, (await comment_responses([item]))[0])


@router.get(
    "/articles/{article_id}/comments/{comment_id}", response_model=ArticleCommentResponse,
    summary="Read an article discussion entry",
    description="Read a scoped comment, including deleted tombstones; inaccessible originals return 404.",
    responses=documented_responses(404, 503),
)
async def get_article_comment(
    article_id: ArticleId, comment_id: CommentId, comments: Comments,
) -> ArticleCommentResponse:
    """Read one comment after checking containing-publication visibility.

    :param article_id: Public containing article identifier.
    :param comment_id: Comment or reply identifier within this publication.
    :param comments: Request-scoped discussion service.
    :return: A live entry or its deleted tombstone.
    """
    item = await comments.get("article", article_id, comment_id)

    return cast(ArticleCommentResponse, (await comment_responses([item]))[0])


@router.patch(
    "/articles/{article_id}/comments/{comment_id}", response_model=ArticleCommentResponse,
    summary="Edit your article discussion entry",
    description="Only the comment author may replace live text. Nesting fields are rejected. "
    "A publication owner has no editing rights over other accounts' comments.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def edit_article_comment(
    _origin: Origin, article_id: ArticleId, comment_id: CommentId, payload: CommentText,
    current_user: CurrentUser, comments: Comments,
) -> ArticleCommentResponse:
    """Replace owned comment text without moving its discussion position.

    :param _origin: Required same-origin mutation header.
    :param article_id: Public containing article identifier.
    :param comment_id: Scoped comment or reply identifier.
    :param payload: Replacement plain text; extra fields are rejected.
    :param current_user: Authenticated account owning this comment.
    :param comments: Request-scoped discussion service.
    :return: The updated entry with its current public author card.
    """
    item = await comments.change("article", article_id, comment_id, current_user, payload)

    return cast(ArticleCommentResponse, (await comment_responses([item]))[0])


@router.delete(
    "/articles/{article_id}/comments/{comment_id}", status_code=204,
    summary="Delete your article discussion entry",
    description="Only the comment author may erase text. Returns a flat tombstone on subsequent reads. "
    "Repeated deletion is idempotent; inaccessible originals return 404.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def delete_article_comment(
    _origin: Origin, article_id: ArticleId, comment_id: CommentId,
    current_user: CurrentUser, comments: Comments,
) -> Response:
    """Erase owned content while retaining discussion identifiers and positions.

    :param _origin: Required same-origin mutation header.
    :param article_id: Public containing article identifier.
    :param comment_id: Scoped comment or reply identifier.
    :param current_user: Authenticated account owning this comment.
    :param comments: Request-scoped discussion service.
    :return: An empty 204 response after the deletion commits.
    """
    await comments.change("article", article_id, comment_id, current_user, None)

    return Response(status_code=204)
