"""Batch discussion authors and map tombstones without leaking erased content."""

from beanie import PydanticObjectId

from backend.comments.models import CommentLike, PostReply
from backend.comments.repository import CommentRepository, Discussion
from backend.comments.schemas import ArticleCommentResponse, PostReplyResponse
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
        list({comment.author_id for comment in comments if comment.deleted_at is None})
    )
    by_id = {author.id: author for author in authors}
    counts = await CommentRepository.child_counts([item.id for item in comments if isinstance(item, PostReply)])
    liked = set()
    if comments and viewer_id is not None:
        reactions = await CommentLike.find({
            "kind": "micro_post" if isinstance(comments[0], PostReply) else "article",
            "comment_id": {"$in": [item.id for item in comments if item.deleted_at is None]},
            "user_id": viewer_id,
        }).to_list()
        liked = {reaction.comment_id for reaction in reactions}

    result: list[PostReplyResponse | ArticleCommentResponse] = []

    for item in comments:
        author = by_id.get(item.author_id) if item.deleted_at is None else None
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

        if isinstance(item, PostReply):
            result.append(
                PostReplyResponse(
                    **common,
                    post_id=str(item.post_id),
                    parent_id=str(item.parent_id) if item.parent_id else None,
                    root_id=str(item.root_id),
                    depth=item.depth,
                    replies_count=counts.get(item.id, 0),
                )
            )
        else:
            result.append(ArticleCommentResponse(**common, article_id=str(item.article_id)))

    return result
