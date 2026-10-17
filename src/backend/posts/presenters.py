"""Pure posts response mapping with an already loaded author."""

from backend.posts.models import MicroPost
from backend.posts.schemas import MicroPostResponse
from backend.profiles.models import User
from backend.profiles.presenters import avatar_url
from backend.publications.urls import share_path
from backend.storage.urls import publication_image_url


def post_response(post: MicroPost, author: User) -> MicroPostResponse:
    """Present a micro-post using its already loaded author.

    :param post: Micro-post document to present.
    :param author: Already loaded account that authored the publication.
    :return: The public micro-post response.
    """
    return MicroPostResponse(
        id=str(post.id),
        share_url=share_path(author.username, post.text, post.share_id),
        text=post.text,
        images=[publication_image_url(key, "post-images") for key in post.image_keys],
        author_id=str(author.id),
        author_username=author.username,
        author_display_name=author.display_name,
        author_avatar_url=avatar_url(author),
        created_at=post.created_at,
        updated_at=post.updated_at,
    )
