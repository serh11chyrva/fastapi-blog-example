"""Hydrate already authorized publication responses with one batched cache read."""

from typing import Any

from pydantic import BaseModel
from redis.asyncio import Redis

from backend.core.errors import InvalidOperation
from backend.links.cache import cached_resolutions
from backend.links.preview import checked_url
from backend.links.schemas import LinkPresentation


def response_publications(value: Any) -> list[LinkPresentation]:
    """Collect publication models from a response without following stored body data.

    :param value: Authorized response model, page, or list of response models.
    :return: Publications, including originals nested in reposts, saves, and discussion entries.
    """
    result = [value] if isinstance(value, LinkPresentation) else []
    if isinstance(value, BaseModel):
        for name in type(value).model_fields:
            if name not in {"body", "link_resolutions"}:
                result.extend(response_publications(getattr(value, name)))
    elif isinstance(value, (list, tuple)):
        for item in value:
            result.extend(response_publications(item))
    return result


def publication_link_urls(publication: LinkPresentation) -> list[str]:
    """Collect normalized external destinations from attachments and article blocks.

    :param publication: Already visible publication response, optionally containing an article body.
    :return: Unique validated URLs used by link, Open Graph, or embed descriptors.
    """
    urls = [
        item.url for item in getattr(publication, "attachments", [])
        if item.type in {"link", "og_card", "embed"}
    ]
    pending = [getattr(publication, "body", None)]
    while pending:
        node = pending.pop()
        if not isinstance(node, dict):
            continue
        if node.get("type") == "attachment":
            attrs = node.get("attrs", {})
            if isinstance(attrs, dict) and attrs.get("type") in {"link", "og_card", "embed"}:
                urls.append(attrs.get("url"))
        pending.extend(node.get("content", []))
    normalized = {}
    for url in urls:
        if not isinstance(url, str):
            continue
        try:
            normalized[checked_url(url)] = None
        except (ValueError, InvalidOperation):
            continue
    return list(normalized)


async def hydrate_publications[T](redis: Redis, value: T) -> T:
    """Attach current cached presentations after visibility checks and feed-cache reads.

    :param redis: Application cache connection; failures leave usable saved descriptors.
    :param value: Response model or list to enrich without modifying persisted documents.
    :return: The same response with per-publication metadata populated by one batched read.
    """
    targets = [(item, publication_link_urls(item)) for item in response_publications(value)]
    urls = list(dict.fromkeys(url for _, links in targets for url in links))
    resolutions = await cached_resolutions(redis, urls)
    for publication, links in targets:
        publication.link_resolutions = {url: resolutions[url] for url in links if url in resolutions}
    return value
