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
    group_for_profile: PydanticObjectId | None = None,
) -> list[dict[str, Any]]:
    """Exclude posts hidden by their archive, original, or any archived ancestor.

    :param prefix: Dotted path to the post, or empty for the aggregation root.
    :param viewer_id: Optional owner for private discussion reads; public lists omit it.
    :param group_for_profile: Profile whose eligible author continuations must be omitted before pagination.
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
        *([grouped_continuation_stage(group_for_profile, prefix)] if group_for_profile is not None else []),
        {"$unset": ["_reply_article", "_reply_post", "_reply_ancestors"]},
    ]


def grouped_continuation_stage(profile_id: PydanticObjectId, prefix: str = "") -> dict[str, Any]:
    """Suppress connected self-replies only when their original belongs to this profile.

    :param profile_id: Profile account whose chronological activity is being selected.
    :param prefix: Optional dotted path to the post inside the aggregation row.
    :return: A filter using the visibility pipeline's already loaded original and ancestor documents.
    """
    path = f"${prefix}." if prefix else "$"
    root_owner = {"$ifNull": [{"$arrayElemAt": ["$_reply_post.owner_id", 0]}, None]}
    root_featured = {"$ifNull": [{"$arrayElemAt": ["$_reply_post.featured_author_ids", 0]}, []]}
    grouped = {"$and": [
        {"$eq": [f"{path}reply.kind", "micro_post"]},
        {"$eq": [f"{path}owner_id", root_owner]},
        {"$or": [{"$eq": [root_owner, profile_id]}, {"$in": [profile_id, root_featured]}]},
        {"$eq": [{"$size": "$_reply_ancestors"}, {"$ifNull": [f"{path}reply.depth", -1]}]},
        {"$allElementsTrue": [{"$map": {
            "input": "$_reply_ancestors", "as": "ancestor", "in": {"$and": [
                {"$eq": ["$$ancestor.owner_id", f"{path}owner_id"]},
                {"$eq": ["$$ancestor.reply.kind", "micro_post"]},
                {"$eq": ["$$ancestor.reply.publication_id", f"{path}reply.publication_id"]},
                {"$ne": ["$$ancestor.pending", True]},
            ]},
        }}]},
    ]}
    return {"$match": {"$expr": {"$not": [grouped]}}}
