"""Repeatable search backfill for a maintenance window with all writers paused."""

from pymongo import AsyncMongoClient

from backend.articles.models import Article
from backend.core.transactions import transaction
from backend.posts.models import MicroPost
from backend.profiles.models import User
from backend.publications.hashtags import extract_hashtags
from backend.search.models import SearchPublication
from backend.search.sync import sync_publication


async def backfill_search(mongo: AsyncMongoClient) -> dict[str, int]:
    """Rebuild projections and profile tags without changing source timestamps or revisions.

    Reruns upsert by unique source identity and remove orphaned projections. Pause
    every application, scheduler, and seed writer for the entire maintenance window.

    :param mongo: Configured MongoDB client used for per-publication transactions.
    :return: Counts of visited publications, profiles, and removed orphan projections.
    """
    counts = {"publications": 0, "profiles": 0, "orphans_removed": 0}
    for model in (MicroPost, Article):
        async for source in model.find_all():
            async with transaction(mongo) as session:
                await sync_publication(source, session)
            counts["publications"] += 1
    async for user in User.find_all():
        tags = extract_hashtags(user.display_name + "\n" + user.bio)
        await User.find_one({"_id": user.id}).update({"$set": {"search_hashtags": tags}})
        counts["profiles"] += 1
    async for projection in SearchPublication.find_all():
        model = Article if projection.source_kind == "article" else MicroPost
        if await model.get(projection.source_id) is None:
            await projection.delete()
            counts["orphans_removed"] += 1
    return counts
