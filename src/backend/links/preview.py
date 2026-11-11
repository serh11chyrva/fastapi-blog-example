"""Retrieve bounded public metadata and select a reachable declared preview image."""

import asyncio
import ipaddress
import socket
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import aiohttp
from aiohttp.abc import AbstractResolver, ResolveResult
from pydantic import BaseModel, ConfigDict

from backend.core.errors import InvalidOperation
from backend.links.platforms import validate_link_url
from backend.publications.attachments import ContentUrl, OpenGraphAttachment

MAX_HTML_BYTES = 512 * 1024
MAX_REDIRECTS = 3
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class LinkPreviewRequest(BaseModel):
    """A public HTTP or HTTPS page to preview."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [{"url": "https://example.com/"}]})

    url: ContentUrl


def public_address(value: str) -> bool:
    """Classify a numeric address before handing it to the HTTP connector.

    :param value: Numeric address returned by the system resolver.
    :return: Whether the address may be contacted by the preview service.
    """
    address = ipaddress.ip_address(value)
    if isinstance(address, ipaddress.IPv6Address) and (address.ipv4_mapped or address.sixtofour):
        return False

    return address.is_global and not (address.is_multicast or address.is_reserved or address.is_link_local)


def public_socket(address: tuple[int, int, int, str, tuple[Any, ...]]) -> socket.socket:
    """Enforce public destinations even when the connector bypasses DNS for a literal.

    :param address: Socket parameters and resolved destination selected by the connector.
    :return: An unconnected socket for an approved address.
    """
    family, socket_type, protocol, _, target = address
    if not public_address(target[0]):
        raise InvalidOperation("Link previews require a public address")

    return socket.socket(family, socket_type, protocol)


class PublicResolver(AbstractResolver):
    """Resolve hostnames once and pass only checked numeric addresses to aiohttp."""

    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET) -> list[ResolveResult]:
        """Resolve and check every candidate before opening a connection.

        :param host: Hostname used for HTTP Host and TLS certificate validation.
        :param port: Target TCP port.
        :param family: Requested socket address family.
        :return: Validated numeric addresses for the original hostname.
        """
        rows = await asyncio.get_running_loop().getaddrinfo(
            host, port, family=family, type=socket.SOCK_STREAM,
        )
        if any(not public_address(address[0]) for _, _, _, _, address in rows):
            raise InvalidOperation("Link previews require a public address")

        return [
            ResolveResult(
                hostname=host, host=address[0], port=port, family=address_family, proto=protocol,
                flags=socket.AI_NUMERICHOST | socket.AI_NUMERICSERV,
            )
            for address_family, _, protocol, _, address in rows
        ]

    async def close(self) -> None:
        """Close the resolver, which holds no persistent state.

        :return: None.
        """


class PageMetadata(HTMLParser):
    """Extract text and ordered Open Graph image groups with Twitter fallbacks."""

    def __init__(self) -> None:
        """Initialize metadata and title tracking.

        :return: None.
        """
        super().__init__()
        self.values: dict[str, str] = {}
        self.images: list[dict[str, str]] = []
        self.twitter_images: list[str] = []
        self.in_title = False
        self.title = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect supported meta fields and detect the title element.

        :param tag: Lowercase HTML tag name.
        :param attrs: Parsed HTML attributes.
        :return: None.
        """
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            fields = dict(attrs)
            key = (fields.get("property") or fields.get("name") or "").lower()
            value = " ".join((fields.get("content") or "").split())
            if not value:
                return
            if key in {"og:title", "og:description", "og:site_name", "description"}:
                self.values.setdefault(key, value)
            elif key in {"og:image", "og:image:url"}:
                self.images.append({"url": value})
            elif key == "og:image:secure_url":
                if not self.images:
                    self.images.append({})
                self.images[-1].setdefault("secure_url", value)
            elif key in {"twitter:image", "twitter:image:src"}:
                self.twitter_images.append(value)

    def image_candidates(self) -> list[str]:
        """List declared images in group order, preferring secure variants.

        :return: Deduplicated Open Graph candidates followed by Twitter candidates.
        """
        candidates = [value for group in self.images for key in ("secure_url", "url") if (value := group.get(key))]
        return list(dict.fromkeys([*candidates, *self.twitter_images]))

    def handle_endtag(self, tag: str) -> None:
        """Stop collecting title text after the closing element.

        :param tag: Lowercase HTML tag name.
        :return: None.
        """
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        """Collect plain title text only.

        :param data: Text delivered by the HTML parser.
        :return: None.
        """
        if self.in_title and len(self.title) < 300:
            self.title = (self.title + data)[:300]


def checked_url(url: str) -> str:
    """Validate a request or redirect target before passing it to the connector.

    :param url: Absolute HTTP or HTTPS URL to inspect.
    :return: The validated destination with the fragment removed.
    """
    try:
        validate_link_url(url)
        parts = urlsplit(url)
        host = parts.hostname or ""
        if "%" in host or host.endswith(".localhost") or "." not in host:
            raise ValueError
        if parts.port not in {None, 443 if parts.scheme == "https" else 80}:
            raise ValueError
        try:
            ipaddress.ip_address(host)
        except ValueError:
            return urlunsplit(parts._replace(fragment=""))

        raise ValueError
    except ValueError as exc:
        raise InvalidOperation("Use a public HTTP(S) hostname on its standard port") from exc


async def fetch_public(url: str, content_type: str) -> tuple[bytes, str] | None:
    """Fetch bounded public content with checked DNS and redirect destinations.

    :param url: Public HTTP(S) destination using standard ports.
    :param content_type: Expected response media type.
    :return: Response bytes and final URL, or None on unavailable or oversized content.
    """
    target = checked_url(url)
    try:
        async with asyncio.timeout(5):
            connector = aiohttp.TCPConnector(
                resolver=PublicResolver(), use_dns_cache=False, force_close=True, socket_factory=public_socket,
            )
            async with aiohttp.ClientSession(
                connector=connector, cookie_jar=aiohttp.DummyCookieJar(), trust_env=False, auto_decompress=False,
            ) as client:
                for step in range(MAX_REDIRECTS + 1):
                    async with client.get(target, allow_redirects=False, headers={"Accept-Encoding": "identity"}) as response:
                        if response.status in REDIRECT_STATUSES:
                            location = response.headers.get("Location")
                            if step == MAX_REDIRECTS or not location:
                                return None
                            target = checked_url(urljoin(target, location))
                            continue
                        if (response.status != 200 or response.content_type != content_type
                            or response.headers.get("Content-Encoding", "identity").lower() != "identity"
                            or (response.content_length or 0) > MAX_HTML_BYTES):
                            return None
                        body = bytearray()
                        async for chunk in response.content.iter_chunked(16384):
                            if len(body) + len(chunk) > MAX_HTML_BYTES:
                                return None
                            body.extend(chunk)
                        return bytes(body), target
    except (aiohttp.ClientError, TimeoutError, LookupError, UnicodeError, InvalidOperation, OSError):
        return None
    return None


async def probe_public_image(url: str) -> str | None:
    """Check an image with a bounded range request and the public fetch protections.

    :param url: Validated public HTTP(S) image candidate.
    :return: Final image URL after at most three redirects, or None when unavailable.
    """
    target = checked_url(url)
    try:
        async with asyncio.timeout(3):
            connector = aiohttp.TCPConnector(
                resolver=PublicResolver(), use_dns_cache=False, force_close=True, socket_factory=public_socket,
            )
            async with aiohttp.ClientSession(
                connector=connector, cookie_jar=aiohttp.DummyCookieJar(), trust_env=False, auto_decompress=False,
            ) as client:
                for step in range(MAX_REDIRECTS + 1):
                    async with client.get(target, allow_redirects=False, headers={
                        "Accept-Encoding": "identity", "Range": "bytes=0-1023",
                    }) as response:
                        if response.status in REDIRECT_STATUSES:
                            location = response.headers.get("Location")
                            if step == MAX_REDIRECTS or not location:
                                return None
                            target = checked_url(urljoin(target, location))
                            if len(target) > 2048:
                                return None
                            continue
                        if (response.status not in {200, 206} or not response.content_type.startswith("image/")
                                or response.headers.get("Content-Encoding", "identity").lower() != "identity"):
                            return None
                        return target if await response.content.read(1024) else None
    except (aiohttp.ClientError, TimeoutError, LookupError, UnicodeError, InvalidOperation, OSError, ValueError):
        return None
    return None


async def select_preview_image(metadata: PageMetadata, base_url: str) -> str | None:
    """Choose a declared, public, reachable image within one bounded probe budget.

    :param metadata: Parsed image groups and Twitter fallbacks.
    :param base_url: Final page URL used to resolve relative image references.
    :return: The first usable candidate, or None after an eight-second total budget.
    """
    try:
        async with asyncio.timeout(8):
            for raw in metadata.image_candidates()[:12]:
                try:
                    candidate = checked_url(urljoin(base_url, raw))
                except (ValueError, InvalidOperation):
                    continue
                if len(candidate) <= 2048 and (image := await probe_public_image(candidate)):
                    return image
    except TimeoutError:
        pass
    return None


async def link_preview(url: str) -> OpenGraphAttachment:
    """Extract public card metadata, falling back to the original hostname.

    :param url: Author-supplied absolute link destination.
    :return: Bounded text and a reachable declared image URL, without executable markup or stored image copies.
    """
    target = checked_url(url)
    host = urlsplit(target).hostname or target
    metadata = PageMetadata()
    response = await fetch_public(target, "text/html")
    image = None
    if response:
        metadata.feed(response[0].decode("utf-8", errors="replace"))
        metadata.close()
        image = await select_preview_image(metadata, response[1])
    return OpenGraphAttachment(
        url=url, title=(metadata.values.get("og:title") or " ".join(metadata.title.split()) or host)[:300],
        description=(metadata.values.get("og:description") or metadata.values.get("description") or "")[:1000],
        site_name=(metadata.values.get("og:site_name") or host)[:200], image_url=image,
    )
