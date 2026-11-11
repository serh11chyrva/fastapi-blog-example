"""Cached link presentations and a persistent, deduplicated resolution queue."""

import hashlib
import time

from loguru import logger
from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from backend.links.preview import checked_url
from backend.core.errors import InvalidOperation
from backend.links.resolution import LinkResolution, fallback_resolution
from backend.publications.attachments import PublicationAttachment

QUEUE = "links:resolve:queue:v1"


class CachedResolution(BaseModel):
    """Retain stale usable metadata while a refresh is queued."""

    result: LinkResolution
    refresh_at: float


def cache_key(url: str) -> str:
    """Build a bounded, versioned cache identity without exposing URLs in key names.

    :param url: Normalized destination URL.
    :return: Redis key for the cached presentation.
    """
    return f"links:metadata:v1:{hashlib.sha256(url.encode()).hexdigest()}"


async def cached_resolution(redis: Redis, url: str) -> LinkResolution:
    """Return cached metadata immediately and enqueue missing or stale URLs once.

    :param redis: Application Redis client.
    :param url: Author-supplied URL, validated before queueing.
    :return: Cached presentation or a usable pending/fallback hostname card.
    """
    target = checked_url(url)
    cached = None
    try:
        raw = await redis.get(cache_key(target))
        if raw:
            try:
                cached = CachedResolution.model_validate_json(raw)
            except ValidationError:
                pass
        if cached is None or cached.refresh_at <= time.time():
            await redis.zadd(QUEUE, {target: time.time()}, nx=True)
        return cached.result if cached else fallback_resolution(target, pending=True)
    except RedisError:
        logger.warning("Link metadata cache unavailable")
        return cached.result if cached else fallback_resolution(target)


async def enqueue_attachments(redis: Redis, attachments: list[PublicationAttachment]) -> None:
    """Schedule URL metadata after a publication transaction has committed.

    :param redis: Application Redis client.
    :param attachments: Saved explicit or article-body descriptors.
    :return: None; unavailable cache infrastructure never fails a saved publication.
    """
    for item in attachments:
        if item.type in {"link", "og_card", "embed"}:
            try:
                await cached_resolution(redis, item.url)
            except (ValueError, InvalidOperation):
                continue
