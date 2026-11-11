from backend.articles.models import Article
from backend.articles.summary import article_summary


async def backfill_summaries() -> int:
    """Replace legacy previews without overwriting concurrent body edits.

    :return: Number of article summaries updated by this resumable pass.
    """
    changed = 0
    async for article in Article.find_all():
        summary = article_summary(article.body)
        if article.summary != summary:
            result = await Article.find({"_id": article.id, "body": article.body}).update_many(
                {"$set": {"summary": summary}}
            )
            changed += result.modified_count

    return changed


async def ensure_public_share_ids() -> None:
    """Backfill stable share keys for existing articles without replacing persisted identities.

    :return: None.
    """
    for item in await Article.find({"share_id": {"$exists": False}}).to_list():
        item.share_id = f"20000000{item.id}"
        await item.save()
