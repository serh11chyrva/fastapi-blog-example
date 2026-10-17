"""Pure posts response mapping with already loaded authors."""

from backend.posts.models import MicroPost
from backend.posts.schemas import MicroPostResponse
from backend.profiles.models import User
from backend.profiles.presenters import user_card
from backend.publications.urls import share_path
from backend.storage.urls import publication_image_url


def post_response(post: MicroPost, authors: list[User]) -> MicroPostResponse:
    """Present a micro-post using its already loaded authors in stored order.

    :param post: Micro-post document to present.
    :param authors: All author accounts in stored order, with the owner first.
    :return: The public micro-post response.
    """
    return MicroPostResponse(
        id=str(post.id),
        owner_id=str(post.owner_id),
        share_url=share_path(authors[0].username, post.text, post.share_id),
        text=post.text,
        images=[publication_image_url(key, "post-images") for key in post.image_keys],
        authors=[user_card(author) for author in authors],
        created_at=post.created_at,
        updated_at=post.updated_at,
    )
