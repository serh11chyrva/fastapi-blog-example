import asyncio
from datetime import UTC, datetime

from loguru import logger
from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from backend.audit.models import AuditEvent
from backend.content.models import Article


async def publish_due_articles(mongo_client: AsyncMongoClient) -> int:
    now = datetime.now(UTC)
    due_articles = await Article.find(
        Article.status == "scheduled",
        Article.scheduled_at <= now,
        Article.deleted_at == None,  # noqa: E711
    ).to_list()
    published_count = 0
    for article in due_articles:
        async with mongo_client.start_session() as db_session:
            async with await db_session.start_transaction():
                current = await Article.get(article.id, session=db_session)
                if current is None or current.status != "scheduled" or current.scheduled_at is None or current.scheduled_at > now:
                    continue
                current.status = "published"
                current.published_at = now
                current.scheduled_at = None
                current.updated_at = now
                await current.save(session=db_session)
                await AuditEvent(
                    actor_id=current.author_id,
                    action="ARTICLE_PUBLISHED",
                    target_type="article",
                    target_id=str(current.id),
                    occurred_at=now,
                    ip_address=None,
                    user_agent=None,
                    metadata={"source": "scheduled_publication"},
                ).insert(session=db_session)
                published_count += 1
    return published_count


async def run_publication_scheduler(mongo_client: AsyncMongoClient, redis_client: Redis) -> None:
    while True:
        try:
            if await publish_due_articles(mongo_client):
                await redis_client.incr("feed:public:version")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduled publication worker failed")
        await asyncio.sleep(15)
