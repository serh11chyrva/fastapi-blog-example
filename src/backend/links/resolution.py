"""Resolve public links into safe cards or provider-confirmed players."""

import json
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel

from backend.links.players import player_resource
from backend.links.preview import fetch_public, link_preview
from backend.publications.attachments import EmbedAttachment, OpenGraphAttachment


class LinkResolution(BaseModel):
    """Cached presentation result; executable provider HTML is never returned."""

    status: Literal["pending", "ready", "fallback"] = "ready"
    card: OpenGraphAttachment
    attachment: EmbedAttachment | OpenGraphAttachment
    player_url: str | None = None


def fallback_resolution(url: str, pending: bool = False) -> LinkResolution:
    """Create a usable hostname card while metadata is missing or unavailable.

    :param url: Validated public HTTP(S) destination.
    :param pending: Whether background work is pending rather than finished unsuccessfully.
    :return: Non-executable link presentation.
    """
    card = OpenGraphAttachment(url=url, title=(urlsplit(url).hostname or url)[:300])
    return LinkResolution(status="pending" if pending else "fallback", card=card, attachment=card)


async def resolve_link(url: str) -> LinkResolution:
    """Fetch bounded metadata and promote only a recognized, provider-confirmed resource.

    :param url: Validated public URL to resolve.
    :return: Card fallback or a player with an independently constructed approved URL.
    """
    card = await link_preview(url)
    resource = player_resource(url)
    if resource:
        provider, canonical, player, endpoint = resource
        response = await fetch_public(endpoint, "application/json")
        if response:
            try:
                metadata = json.loads(response[0])
                if isinstance(metadata, dict) and metadata.get("type") in {"video", "rich"} and "<iframe" in str(
                    metadata.get("html", ""),
                ).lower():
                    title = metadata.get("title")
                    if isinstance(title, str) and title.strip():
                        card.title = title.strip()[:300]
                    return LinkResolution(
                        card=card, attachment=EmbedAttachment(provider=provider, url=canonical), player_url=player,
                    )
            except (ValueError, TypeError):
                pass
    return LinkResolution(status="fallback" if resource else "ready", card=card, attachment=card)
