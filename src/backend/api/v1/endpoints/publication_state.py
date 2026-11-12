"""HTTP adapters for owner archives and public profile pins."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from backend.api import examples
from backend.api.metadata import ArticleId, Origin, PostId, Username, documented_responses
from backend.articles.models import Article
from backend.articles.presenters import article_response
from backend.articles.schemas import ArticleResponse
from backend.audit.dependencies import Audit
from backend.auth.dependencies import CurrentUser
from backend.core.resources import Resources
from backend.feeds.schemas import ArticleFeedItem, PostFeedItem
from backend.links.presentation import hydrate_publications
from backend.posts.models import MicroPost
from backend.posts.presenters import post_response
from backend.posts.schemas import MicroPostResponse
from backend.profiles.queries import ProfileQueries
from backend.publications.access import publication_is_public
from backend.publications.queries import load_authors
from backend.publications.schemas import ArchivePage
from backend.publications.service import PublicationStateService

router = APIRouter(tags=["Publication state"])


def get_state_service(resources: Resources, audit: Audit) -> PublicationStateService:
    """Create the publication-state service for this request.

    :param resources: Application-owned infrastructure clients.
    :param audit: Request audit metadata.
    :return: The configured publication-state service.
    """
    return PublicationStateService(resources, audit)


States = Annotated[PublicationStateService, Depends(get_state_service)]


async def state_response(
    item: MicroPost | Article, states: PublicationStateService,
) -> MicroPostResponse | ArticleResponse:
    """Present a committed publication with current authors and cached link metadata.

    :param item: Owned post or article returned by the state service.
    :param states: Service holding the application cache connection.
    :return: The updated publication including its archive and pin timestamps.
    """
    authors = await load_authors(item.author_ids)
    result = post_response(item, authors) if isinstance(item, MicroPost) else article_response(item, authors)
    if isinstance(item, MicroPost) and item.reply is not None:
        result.read_only = not await publication_is_public("micro_post", str(item.id))
    return await hydrate_publications(states.resources.redis, result)


@router.put(
    "/posts/{post_id}/archive", response_model=MicroPostResponse,
    summary="Archive your post or reply",
    description="Make your post and its discussion owner-only, preserve content, and clear its pin. "
    "Repeated requests preserve archived_at. Upload drafts cannot be archived.",
    responses=documented_responses(401, 403, 404, 409, 422, 503,
                                   examples=[(examples.POST_ARCHIVED, "Private archived post")]),
)
@router.delete(
    "/posts/{post_id}/archive", response_model=MicroPostResponse,
    summary="Unarchive your post or reply",
    description="Clear archived_at without changing content timestamps or restoring a pin. "
    "Replies still require their original and ancestors to be public to appear publicly.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def set_post_archive(
    _origin: Origin, post_id: PostId, current_user: CurrentUser, states: States, request: Request, response: Response,
) -> MicroPostResponse:
    """Set archive state for an owned post, preserving content and discussion records.

    :param _origin: Required same-origin mutation header.
    :param post_id: Owned post or reply identifier.
    :param current_user: Authenticated publication owner.
    :param states: Request-scoped publication-state service.
    :param request: HTTP method selecting archive or restore.
    :param response: HTTP response for the private cache policy.
    :return: The post with committed state timestamps.
    """
    response.headers["Cache-Control"] = "private, no-store"
    item = await states.change("micro_post", post_id, "archive", request.method == "PUT", current_user)
    return await state_response(item, states)


@router.put(
    "/articles/{article_id}/archive", response_model=ArticleResponse,
    summary="Archive your published article",
    description="Make a published article and its discussion owner-only and clear its pin. "
    "Preserve status and published_at; drafts and scheduled articles return 422.",
    responses=documented_responses(401, 403, 404, 409, 422, 503,
                                   examples=[(examples.ARTICLE_ARCHIVED, "Private archived article")]),
)
@router.delete(
    "/articles/{article_id}/archive", response_model=ArticleResponse,
    summary="Unarchive your article",
    description="Restore public visibility with the original publication date and without a pin.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def set_article_archive(
    _origin: Origin, article_id: ArticleId, current_user: CurrentUser,
    states: States, request: Request, response: Response,
) -> ArticleResponse:
    """Set archive state for an owned published article.

    :param _origin: Required same-origin mutation header.
    :param article_id: Owned article identifier.
    :param current_user: Authenticated publication owner.
    :param states: Request-scoped publication-state service.
    :param request: HTTP method selecting archive or restore.
    :param response: HTTP response for the private cache policy.
    :return: The article with committed state timestamps.
    """
    response.headers["Cache-Control"] = "private, no-store"
    item = await states.change("article", article_id, "archive", request.method == "PUT", current_user)
    return await state_response(item, states)


@router.put(
    "/posts/{post_id}/pin", response_model=MicroPostResponse,
    summary="Pin your public post or reply",
    description="Pin a public owned post in your profile. The shared limit across posts, replies, and articles is five; "
    "a sixth pin returns 409. Archived posts cannot be pinned. Repeating a pin preserves pinned_at.",
    responses=documented_responses(401, 403, 404, 409, 422, 503,
                                   examples=[(examples.POST_PINNED, "Post pinned in its owner's profile")]),
)
@router.delete(
    "/posts/{post_id}/pin", response_model=MicroPostResponse,
    summary="Unpin your post or reply", description="Clear pinned_at; repeating the request is safe.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def set_post_pin(
    _origin: Origin, post_id: PostId, current_user: CurrentUser, states: States, request: Request, response: Response,
) -> MicroPostResponse:
    """Set profile pin state for an owned post or reply.

    :param _origin: Required same-origin mutation header.
    :param post_id: Owned post or reply identifier.
    :param current_user: Authenticated publication owner.
    :param states: Request-scoped publication-state service.
    :param request: HTTP method selecting pin or unpin.
    :param response: HTTP response for the private cache policy.
    :return: The post with committed state timestamps.
    """
    response.headers["Cache-Control"] = "private, no-store"
    item = await states.change("micro_post", post_id, "pin", request.method == "PUT", current_user)
    return await state_response(item, states)


@router.put(
    "/articles/{article_id}/pin", response_model=ArticleResponse,
    summary="Pin your published article",
    description="Pin a public owned article in your profile's Articles tab. At most five publications may be pinned "
    "across all types. Archived, draft, and scheduled articles cannot be pinned.",
    responses=documented_responses(401, 403, 404, 409, 422, 503),
)
@router.delete(
    "/articles/{article_id}/pin", response_model=ArticleResponse,
    summary="Unpin your article", description="Clear pinned_at; repeating the request is safe.",
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def set_article_pin(
    _origin: Origin, article_id: ArticleId, current_user: CurrentUser,
    states: States, request: Request, response: Response,
) -> ArticleResponse:
    """Set profile pin state for an owned article.

    :param _origin: Required same-origin mutation header.
    :param article_id: Owned article identifier.
    :param current_user: Authenticated publication owner.
    :param states: Request-scoped publication-state service.
    :param request: HTTP method selecting pin or unpin.
    :param response: HTTP response for the private cache policy.
    :return: The article with committed state timestamps.
    """
    response.headers["Cache-Control"] = "private, no-store"
    item = await states.change("article", article_id, "pin", request.method == "PUT", current_user)
    return await state_response(item, states)


@router.get(
    "/me/archive", response_model=ArchivePage, summary="List your archived publications",
    description="Owner-only posts, replies, and published articles, ordered by archived_at, kind, and ID descending. "
    "Archive size is unlimited. Pass next_cursor unchanged to continue.",
    responses=documented_responses(401, 422, 503, examples=[(examples.ARCHIVE_PAGE, "Owned mixed archive")]),
)
async def get_archive(
    current_user: CurrentUser, states: States, response: Response,
    cursor: str | None = Query(default=None, max_length=512, description="Previous archive cursor."),
    limit: int = Query(default=20, ge=1, le=100, description="Archive page size, from 1 to 100."),
) -> ArchivePage:
    """Read only the authenticated account's archive.

    :param current_user: Authenticated archive owner.
    :param states: Request-scoped publication-state service.
    :param response: HTTP response for the private cache policy.
    :param cursor: Previous archive cursor, or None for the first page.
    :param limit: Bounded archive page size.
    :return: Archived publication cards and an optional continuation cursor.
    """
    response.headers["Cache-Control"] = "private, no-store"
    return await hydrate_publications(states.resources.redis, await states.archive(current_user, cursor, limit))


@router.get(
    "/users/{username}/pins", response_model=list[PostFeedItem | ArticleFeedItem],
    summary="List public profile pins",
    description="Up to five currently public owned publications, newest pin first. "
    "Pins are separate from chronological timeline and publication pages; inaccessible replies are omitted.",
    responses=documented_responses(404, 503, examples=[(examples.PROFILE_PINS, "Public profile pins")]),
)
async def get_profile_pins(
    username: Username, states: States, response: Response,
) -> list[PostFeedItem | ArticleFeedItem]:
    """Read a profile's currently visible pins without granting private access.

    :param username: Public profile handle.
    :param states: Request-scoped publication-state service.
    :param response: HTTP response for the visibility-sensitive cache policy.
    :return: Public cards ordered by pin time, kind, and ID descending.
    """
    response.headers["Cache-Control"] = "no-store"
    user = await ProfileQueries().by_username(username)
    return await hydrate_publications(states.resources.redis, await states.pins(user.id))
