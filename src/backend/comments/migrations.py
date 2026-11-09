"""Initialize reaction counters on discussion documents created before reactions."""

from backend.comments.models import ArticleComment, PostReply


async def ensure_comment_like_counts() -> None:
    """Initialize absent counters without changing previously recorded reactions.

    :return: None.
    """
    for model in (ArticleComment, PostReply):
        await model.find({"likes_count": {"$exists": False}}).update_many({"$set": {"likes_count": 0}})
