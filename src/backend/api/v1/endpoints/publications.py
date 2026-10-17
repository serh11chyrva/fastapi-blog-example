"""HTTP adapter for shared public publication links."""

from fastapi import APIRouter

from backend.api import examples
from backend.api.metadata import ShareSlug, Username, documented_responses
from backend.articles.presenters import article_response
from backend.articles.schemas import ArticleResponse
from backend.posts.models import MicroPost
from backend.posts.presenters import post_response
from backend.posts.schemas import MicroPostResponse
from backend.publications.queries import shared

router = APIRouter()


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
