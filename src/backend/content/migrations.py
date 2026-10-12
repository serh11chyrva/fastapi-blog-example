from backend.content.models import Article, MicroPost


async def ensure_public_share_ids() -> None:
    """Backfill stable share keys for publications already in the demo database."""
    for post in await MicroPost.find({"share_id": {"$exists": False}}).to_list():
        post.share_id = f"10000000{post.id}"
        await post.save()
    for article in await Article.find({"share_id": {"$exists": False}}).to_list():
        article.share_id = f"20000000{article.id}"
        await article.save()
