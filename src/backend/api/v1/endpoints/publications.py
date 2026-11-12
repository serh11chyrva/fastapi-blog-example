"""HTTP adapter for shared public publication links."""

from typing import Annotated

from fastapi import APIRouter, Query, Response

from backend.api import examples
from backend.auth.dependencies import OptionalUser
from backend.core.resources import Resources
from backend.api.metadata import ShareSlug, Username, documented_responses
from backend.articles.presenters import article_response
from backend.articles.schemas import ArticleResponse
from backend.links.presentation import hydrate_publications
from backend.posts.models import MicroPost
from backend.feeds.schemas import PublicationPreview
from backend.posts.presenters import post_response
from backend.posts.schemas import MicroPostResponse
from backend.publications.access import publication_is_public
from backend.publications.queries import publication_previews, shared

router = APIRouter()


@router.get(
    "/publications/previews", response_model=list[PublicationPreview],
    summary="Read public cards for publication references",
    description="Pass up to 30 repeated article:<id> or micro_post:<id> references. Unavailable originals are omitted.",
    tags=["Publications"], responses=documented_responses(422, 503),
)
async def get_publication_previews(
    response: Response,
    ref: Annotated[list[str], Query(min_length=1, max_length=30, description="Repeated typed publication reference.")],
) -> list[PublicationPreview]:
    """Read a bounded batch of compact, nonrecursive public cards.

    :param response: HTTP response for the visibility-sensitive cache policy.
    :param ref: Typed references whose public cards are requested.
    :return: Current cards in request order, omitting unavailable originals.
    """
    response.headers["Cache-Control"] = "no-store"

    return await publication_previews(ref)


@router.get(
    "/publications/{username}/{share_slug}",
    response_model=MicroPostResponse | ArticleResponse,
    summary="Read a shared publication",
    openapi_extra={"security": [{}, {"SessionCookie": []}]},
    description=("Resolves the UUID-safe slug in /@username/slug--share-id and returns a public publication, or archived content only for its owner."),
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
    resources: Resources,
    current_user: OptionalUser,
    response: Response,
) -> MicroPostResponse | ArticleResponse:
    """Resolve a public or owner-only archived publication by handle and share slug.

    Cached link presentations are attached after access checks; missing metadata is queued, not fetched here.

    :param username: Public profile handle, optionally prefixed with @.
    :param share_slug: Readable share slug ending with the stable publication share ID.
    :param resources: Application cache used to attach current link presentations.
    :param current_user: Optional session for owner-only archived reads.
    :param response: HTTP response for the private cache policy.
    :return: The accessible post or article response.
    """
    response.headers["Cache-Control"] = "private, no-store"
    publication, authors = await shared(username, share_slug, current_user.id if current_user else None)

    if isinstance(publication, MicroPost):
        result = post_response(publication, authors)
        if publication.reply is not None:
            result.read_only = not await publication_is_public("micro_post", str(publication.id))
    else:
        result = article_response(publication, authors)
    return await hydrate_publications(resources.redis, result)
