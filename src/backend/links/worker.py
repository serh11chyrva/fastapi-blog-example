"""Run the bounded link metadata worker independently of API processes."""

import asyncio
import time
from uuid import uuid4

from loguru import logger
from redis.asyncio import Redis

from backend.core.config import get_settings
from backend.links.cache import QUEUE, CachedResolution, cache_key
from backend.links.resolution import fallback_resolution, resolve_link


async def process_link(redis: Redis, url: str) -> None:
    """Lease a durable queue entry and acknowledge only after caching its result.

    :param redis: Worker Redis connection.
    :param url: Normalized queued destination.
    :return: None; crashes leave the entry available after its short lease expires.
    """
    key = cache_key(url)
    lease = f"{key}:lease"
    token = uuid4().hex
    if not await redis.set(lease, token, nx=True, ex=60):
        return
    try:
        try:
            async with asyncio.timeout(20):
                result = await resolve_link(url)
        except Exception:
            logger.warning("Link metadata resolution failed")
            result = fallback_resolution(url)
        attempts = await redis.incr(f"{key}:attempts")
        await redis.expire(f"{key}:attempts", 86400)
        failed = result.status == "fallback"
        cached = CachedResolution(result=result, refresh_at=time.time() + (300 if failed else 21600))
        async with redis.pipeline(transaction=True) as pipeline:
            pipeline.set(key, cached.model_dump_json(), ex=86400)
            if failed and attempts < 3:
                pipeline.zadd(QUEUE, {url: time.time() + 30 * 2 ** attempts})
            else:
                pipeline.zrem(QUEUE, url)
                pipeline.delete(f"{key}:attempts")
            await pipeline.execute()
    finally:
        await redis.eval(
            "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end",
            1, lease, token,
        )


async def run_worker() -> None:
    """Resolve at most four URLs concurrently, retrying unavailable infrastructure.

    :return: None; the process runs until cancelled.
    """
    redis = Redis.from_url(
        get_settings().redis_url, decode_responses=True, socket_connect_timeout=3, socket_timeout=5,
    )
    try:
        while True:
            try:
                urls = await redis.zrangebyscore(QUEUE, "-inf", time.time(), start=0, num=4)
                if urls:
                    results = await asyncio.gather(*(process_link(redis, url) for url in urls), return_exceptions=True)
                    if any(isinstance(result, BaseException) for result in results):
                        logger.warning("Link worker batch interrupted; unacknowledged jobs remain queued")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Link worker queue unavailable")
            await asyncio.sleep(2)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run_worker())
