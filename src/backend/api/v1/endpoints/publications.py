"""HTTP adapter for shared public publication links."""

from typing import Annotated

from fastapi import APIRouter, Query, Response

from backend.api import examples
from backend.api.metadata import ShareSlug, Username, documented_responses
from backend.articles.presenters import article_response
from backend.articles.schemas import ArticleResponse
from backend.posts.models import MicroPost
from backend.feeds.schemas import PublicationPreview
from backend.posts.presenters import post_response
from backend.posts.schemas import MicroPostResponse
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
) -> MicroPostResponse | ArticleResponse:
    """Resolve a public publication using its owner's handle and share slug.

    :param username: Public profile handle, optionally prefixed with @.
    :param share_slug: Readable share slug ending with the stable publication share ID.
    :return: The matching micro-post or published article response.
    """
    publication, authors = await shared(username, share_slug)

    return (
        post_response(publication, authors)
        if isinstance(publication, MicroPost)
        else article_response(publication, authors)
    )
