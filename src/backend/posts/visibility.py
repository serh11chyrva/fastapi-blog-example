"""Filter original and ancestor visibility before pagination and counting."""

from typing import Any

from beanie import PydanticObjectId


def archive_filter(viewer_id: PydanticObjectId | None, prefix: str = "") -> dict[str, Any]:
    """Build archive visibility for a root document or nested aggregation row.

    :param viewer_id: Optional owner allowed to read its own archived publications.
    :param prefix: Optional dotted document path, without a trailing dot.
    :return: A predicate treating absent archive fields as unarchived.
    """
    path = f"{prefix}." if prefix else ""
    public = {f"{path}archived_at": None}
    return {"$or": [public, {f"{path}owner_id": viewer_id}]} if viewer_id is not None else public


def visible_post_stages(
    prefix: str = "", viewer_id: PydanticObjectId | None = None,
) -> list[dict[str, Any]]:
    """Exclude posts hidden by their archive, original, or any archived ancestor.

    :param prefix: Dotted path to the post, or empty for the aggregation root.
    :param viewer_id: Optional owner for private discussion reads; public lists omit it.
    :return: Visibility stages applied before pagination, ranking, or counting.
    """
    path = f"{prefix}." if prefix else ""
    hidden: dict[str, Any] = {"archived_at": {"$ne": None}}
    if viewer_id is not None:
        hidden["owner_id"] = {"$ne": viewer_id}
    return [
        {"$match": {f"{path}pending": {"$ne": True}, **archive_filter(viewer_id, prefix)}},
        {"$lookup": {
            "from": "articles", "localField": f"{path}reply.publication_id", "foreignField": "_id",
            "as": "_reply_article", "pipeline": [{"$match": {
                "deleted_at": None, "status": "published", **archive_filter(viewer_id),
            }}],
        }},
        {"$lookup": {
            "from": "micro_posts", "localField": f"{path}reply.publication_id", "foreignField": "_id",
            "as": "_reply_post", "pipeline": [{"$match": {
                "deleted_at": None, "reply": None, "pending": {"$ne": True}, **archive_filter(viewer_id),
            }}],
        }},
        {"$graphLookup": {
            "from": "micro_posts", "startWith": f"${path}reply.parent_id",
            "connectFromField": "reply.parent_id", "connectToField": "_id", "as": "_reply_ancestors",
        }},
        {"$match": {"_reply_ancestors": {"$not": {"$elemMatch": hidden}}, "$or": [
            {f"{path}reply": None},
            {f"{path}reply.kind": "article", "_reply_article.0": {"$exists": True}},
            {f"{path}reply.kind": "micro_post", "_reply_post.0": {"$exists": True}},
        ]}},
        {"$unset": ["_reply_article", "_reply_post", "_reply_ancestors"]},
    ]
