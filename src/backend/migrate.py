"""Run explicit, resumable content migrations against configured infrastructure."""

import argparse
import asyncio

from beanie import init_beanie
from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from backend.articles.migrations import backfill_summaries
from backend.core.config import get_settings
from backend.core.database import DOCUMENT_MODELS
from backend.feeds.cache import invalidate_public_feed


async def migrate(operation: str) -> None:
    """Initialize resources and run the requested content conversion.

    :param operation: Explicit migration name selected by the operator.
    :return: None.
    """
    settings = get_settings()
    mongo = AsyncMongoClient(settings.mongodb_url, tz_aware=True)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await init_beanie(database=mongo[settings.mongodb_database], document_models=DOCUMENT_MODELS)
        if operation == "summaries":
            print(f"Updated {await backfill_summaries()} article summaries.")
        await invalidate_public_feed(redis)
    finally:
        await redis.aclose()
        await mongo.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["summaries"])
    asyncio.run(migrate(parser.parse_args().operation))
