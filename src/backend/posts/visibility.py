"""Apply original-publication visibility to reply posts before pagination."""

from typing import Any


def visible_post_stages(prefix: str = "") -> list[dict[str, Any]]:
    """Build joins that exclude replies whose original is no longer public.

    :param prefix: Dotted path to the post in an aggregation row, or empty for the root.
    :return: Aggregation stages retaining ordinary posts and publicly rooted replies.
    """
    path = f"{prefix}." if prefix else ""
    return [
        {"$match": {f"{path}pending": {"$ne": True}}},
        {"$lookup": {
            "from": "articles", "localField": f"{path}reply.publication_id", "foreignField": "_id",
            "as": "_reply_article", "pipeline": [{"$match": {"deleted_at": None, "status": "published"}}],
        }},
        {"$lookup": {
            "from": "micro_posts", "localField": f"{path}reply.publication_id", "foreignField": "_id",
            "as": "_reply_post", "pipeline": [{"$match": {"deleted_at": None, "reply": None, "pending": {"$ne": True}}}],
        }},
        {"$match": {"$or": [
            {f"{path}reply": None},
            {f"{path}reply.kind": "article", "_reply_article.0": {"$exists": True}},
            {f"{path}reply.kind": "micro_post", "_reply_post.0": {"$exists": True}},
        ]}},
        {"$unset": ["_reply_article", "_reply_post"]},
    ]
