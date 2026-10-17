from backend.articles.models import Article


async def ensure_public_share_ids() -> None:
    """Backfill stable share keys for existing articles without replacing persisted identities.

    :return: None.
    """
    for item in await Article.find({"share_id": {"$exists": False}}).to_list():
        item.share_id = f"20000000{item.id}"
        await item.save()
