import asyncio
from datetime import UTC, datetime

from loguru import logger
from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.content.cache import invalidate_public_feed
from backend.content.models import Article
from backend.core.transactions import transaction


async def publish_due_articles(mongo_client: AsyncMongoClient) -> int:
    """Publish a bounded batch, rechecking schedule and deletion in each transaction.

    :param mongo_client: Async MongoDB client used for audited publication transactions.
    :return: The number of articles published by this batch.
    """
    now = datetime.now(UTC)
    due_articles = (
        await Article.find(
            Article.status == "scheduled",
            Article.scheduled_at <= now,
            Article.deleted_at == None,  # noqa: E711
        )
        .sort(("scheduled_at", 1), ("_id", 1))
        .limit(100)
        .to_list()
    )
    published_count = 0

    for article in due_articles:
        async with transaction(mongo_client) as db_session:
            current = await Article.get(article.id, session=db_session)

            if (
                current is None
                or current.deleted_at is not None
                or current.status != "scheduled"
                or current.scheduled_at is None
                or current.scheduled_at > now
            ):
                continue

            current.status = "published"
            current.published_at = now
            current.scheduled_at = None
            current.updated_at = now
            await current.save(session=db_session)
            await record_audit(
                AuditContext(),
                "ARTICLE_PUBLISHED",
                actor_id=current.author_id,
                target_type="article",
                target_id=str(current.id),
                metadata={"source": "scheduled_publication"},
                session=db_session,
            )
            published_count += 1

    return published_count


async def run_publication_scheduler(mongo_client: AsyncMongoClient, redis_client: Redis) -> None:
    """Periodically publish due articles and invalidate the public feed.

    :param mongo_client: Async MongoDB client used for audited publication transactions.
    :param redis_client: Redis client used to invalidate public feed caches.
    :return: None; the worker runs until cancelled.
    """
    while True:
        try:
            if await publish_due_articles(mongo_client):
                await invalidate_public_feed(redis_client)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduled publication worker failed")

        await asyncio.sleep(15)
