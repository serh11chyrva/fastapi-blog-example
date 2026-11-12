"""Batch discussion authors and map tombstones without leaking erased content."""

from beanie import PydanticObjectId

from backend.comments.repository import CommentRepository, Discussion
from backend.comments.schemas import ArticleCommentResponse, PostReplyResponse
from backend.interactions.models import PublicationInteraction
from backend.posts.models import MicroPost
from backend.posts.presenters import post_response
from backend.posts.visibility import visible_post_stages
from backend.profiles.presenters import user_card
from backend.profiles.repository import ProfileRepository


async def comment_responses(
    comments: list[Discussion], viewer_id: PydanticObjectId | None = None,
) -> list[PostReplyResponse | ArticleCommentResponse]:
    """Present a bounded discussion page with batched author and direct-child lookups.

    :param comments: Scoped comments in the caller's requested order.
    :param viewer_id: Current account for reaction flags, or None for anonymous reads.
    :return: Public comments; tombstones hide text and author while preserving identifiers and tree positions.
    """
    authors = await ProfileRepository.users_by_ids(
        list({comment.owner_id for comment in comments if comment.deleted_at is None})
    )
    by_id = {author.id: author for author in authors}
    counts = await CommentRepository.child_counts([item.id for item in comments], viewer_id)
    liked = set()
    if comments and viewer_id is not None:
        reactions = await PublicationInteraction.find({
            "publication_kind": "micro_post", "action": "like",
            "publication_id": {"$in": [item.id for item in comments if item.deleted_at is None]},
            "user_id": viewer_id,
        }).to_list()
        liked = {reaction.publication_id for reaction in reactions}

    public_rows = await MicroPost.aggregate([
        {"$match": {"_id": {"$in": [item.id for item in comments]}, "deleted_at": None}},
        *visible_post_stages(), {"$project": {"_id": 1}},
    ]).to_list() if comments else []
    public_ids = {row["_id"] for row in public_rows}

    result: list[PostReplyResponse | ArticleCommentResponse] = []

    for item in comments:
        author = by_id.get(item.owner_id) if item.deleted_at is None else None
        common = dict(
            id=str(item.id),
            author=user_card(author) if author is not None else None,
            text=item.text if item.deleted_at is None else None,
            created_at=item.created_at,
            updated_at=item.updated_at,
            deleted=item.deleted_at is not None,
            likes_count=item.likes_count if item.deleted_at is None else 0,
            liked=item.id in liked,
        )

        publication = post_response(item, [author]) if author is not None else None
        if publication is not None:
            publication.read_only = item.id not in public_ids
        context = item.reply
        response_type = PostReplyResponse if context.kind == "micro_post" else ArticleCommentResponse
        result.append(response_type(
            **common,
            post_id=str(context.publication_id) if context.kind == "micro_post" else None,
            article_id=str(context.publication_id) if context.kind == "article" else None,
            parent_id=str(context.parent_id) if context.parent_id else None,
            root_id=str(context.root_id), depth=context.depth, replies_count=counts.get(item.id, 0),
            publication=publication,
        ))

    return result
