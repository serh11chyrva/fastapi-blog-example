"""Best-effort invalidation shared by publication and image operations."""

from loguru import logger
from redis.asyncio import Redis
from redis.exceptions import RedisError


async def invalidate_public_feed(redis: Redis) -> None:
    """Advance the public feed cache version when Redis is available.

    :param redis: Redis client used for public feed cache versioning.
    :return: None.
    """
    try:
        await redis.incr("feed:public:version")
    except RedisError:
        logger.warning("Redis unavailable while invalidating public feed cache")
