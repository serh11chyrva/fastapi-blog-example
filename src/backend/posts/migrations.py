from backend.posts.models import MicroPost


async def ensure_public_share_ids() -> None:
    """Backfill stable share keys for existing posts without replacing persisted identities.

    :return: None.
    """
    for item in await MicroPost.find({"share_id": {"$exists": False}}).to_list():
        item.share_id = f"10000000{item.id}"
        await item.save()
