"""Present one authorized discussion path without loading sibling branches."""

from typing import Annotated

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

from backend.api import examples
from backend.articles.models import Article
from backend.core.errors import NotFound
from backend.feeds.presenters import feed_item
from backend.feeds.schemas import ArticleFeedItem, PostFeedItem
from backend.posts.models import MicroPost
from backend.posts.presenters import post_response
from backend.posts.schemas import MicroPostResponse, ReplyTombstone
from backend.profiles.repository import ProfileRepository
from backend.publications.access import readable_publication_path

ContextPost = Annotated[MicroPostResponse | ReplyTombstone, Field(discriminator="kind")]


class PostContext(BaseModel):
    """Selected post, its original publication, and ancestors in reading order."""

    model_config = ConfigDict(json_schema_extra={"examples": [
        {"post": examples.POST, "original": None, "ancestors": []},
        {"post": examples.POST_REPLY_CHILD["publication"], "original": examples.FEED_POST,
         "ancestors": [examples.POST_REPLY["publication"]]},
    ]})

    post: ContextPost = Field(description="Selected live post or a content-free deleted reply.")
    original: PostFeedItem | ArticleFeedItem | None = Field(
        default=None, description="Original post or compact article; null for a standalone selected post.",
    )
    ancestors: list[ContextPost] = Field(default_factory=list, description="Replies from oldest ancestor to parent.")
    read_only: bool = Field(default=False, description="Whether an archived dependency prevents discussion writes.")


def reply_tombstone(post: MicroPost) -> ReplyTombstone:
    """Erase all presentation content from a deleted reply document.

    :param post: Deleted short publication with preserved discussion metadata.
    :return: A navigation-only tombstone with no text, author, attachments, or share slug.
    """
    if post.reply is None or post.deleted_at is None:
        raise ValueError("A tombstone requires a deleted reply")
    return ReplyTombstone(id=str(post.id), reply=post.reply, created_at=post.created_at, updated_at=post.updated_at)


async def post_context(post_id: str, viewer_id: PydanticObjectId | None = None) -> PostContext:
    """Read one complete authorized path and batch all live author presentations.

    :param post_id: Selected post or deleted reply identifier.
    :param viewer_id: Optional owner allowed to read its archived content.
    :return: Ordered context with inherited read-only state and content-free tombstones.
    """
    path = await readable_publication_path("micro_post", post_id, viewer_id, allow_deleted_reply=True)
    selected = path[0]
    original = path[1] if len(path) > 1 else None
    ancestors = list(reversed(path[2:]))
    ordered = ([original] if original else []) + ancestors + [selected]
    ids = list({author_id for item in ordered if item.deleted_at is None for author_id in item.author_ids})
    authors = {user.id: user for user in await ProfileRepository.users_by_ids(ids)} if ids else {}
    original_card = None
    cards: list[MicroPostResponse | ReplyTombstone] = []
    read_only = False
    for item in ordered:
        read_only = read_only or item.archived_at is not None
        if item.deleted_at is not None:
            cards.append(reply_tombstone(item))
            continue
        if any(author_id not in authors for author_id in item.author_ids):
            raise NotFound("Author not found")
        credited = [authors[author_id] for author_id in item.author_ids]
        if original is not None and item.id == original.id:
            original_card = feed_item(item, credited)
        elif isinstance(item, MicroPost):
            card = post_response(item, credited)
            card.read_only = read_only
            cards.append(card)
        elif isinstance(item, Article):
            raise ValueError("Only the original context may be an article")
    return PostContext(post=cards[-1], original=original_card, ancestors=cards[:-1], read_only=read_only)
