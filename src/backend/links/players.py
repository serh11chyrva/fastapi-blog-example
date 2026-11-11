"""Recognize concrete media resources without trusting arbitrary embed markup."""

import re
from urllib.parse import parse_qs, quote, urlencode, urlsplit


def player_resource(url: str) -> tuple[str, str, str, str] | None:
    """Classify supported resource URLs and construct approved player and oEmbed URLs.

    :param url: Absolute author-supplied resource URL.
    :return: Provider, canonical resource, player URL, and oEmbed request; None for unsupported URLs.
    """
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in {None, 443}:
        return None
    host = parsed.hostname
    path = parsed.path.strip("/").split("/")
    query = parse_qs(parsed.query)
    provider = ""
    canonical = player = endpoint = ""
    if host in {"youtube.com", "www.youtube.com", "www.youtube-nocookie.com", "youtu.be"}:
        identity = path[0] if host == "youtu.be" and len(path) == 1 else (
            query.get("v", [""])[0] if path == ["watch"] else
            path[1] if len(path) == 2 and path[0] in {"embed", "shorts", "live"} else ""
        )
        if re.fullmatch(r"[\w-]{11}", identity, re.ASCII):
            provider, canonical = "youtube", f"https://www.youtube.com/watch?v={identity}"
            player, endpoint = f"https://www.youtube-nocookie.com/embed/{identity}", "https://www.youtube.com/oembed"
    elif host in {"vimeo.com", "www.vimeo.com", "player.vimeo.com"}:
        identity = path[0] if len(path) == 1 else path[1] if len(path) == 2 and path[0] == "video" else ""
        if re.fullmatch(r"[0-9]{1,20}", identity):
            provider, canonical = "vimeo", f"https://vimeo.com/{identity}"
            player, endpoint = f"https://player.vimeo.com/video/{identity}", "https://vimeo.com/api/oembed.json"
            secret = query.get("h", [""])[0]
            if re.fullmatch(r"[a-fA-F0-9]{1,32}", secret):
                canonical += f"?h={secret}"
                player += f"?h={secret}"
    elif host == "open.spotify.com":
        path = path[1:] if path[0] == "embed" or path[0].startswith("intl-") else path
        if len(path) == 2 and path[0] in {"track", "album", "playlist", "episode", "show"} and re.fullmatch(
            r"[a-zA-Z0-9]{22}", path[1],
        ):
            provider, canonical = "spotify", f"https://open.spotify.com/{'/'.join(path)}"
            player, endpoint = f"https://open.spotify.com/embed/{'/'.join(path)}", "https://open.spotify.com/oembed"
    elif host in {"soundcloud.com", "www.soundcloud.com"}:
        if re.fullmatch(r"[\w-]+/(?:sets/)?[\w-]+", parsed.path.strip("/"), re.ASCII) and path[0] not in {
            "discover", "search", "charts", "you", "stream", "upload", "settings",
        }:
            provider, canonical = "soundcloud", f"https://soundcloud.com/{parsed.path.strip('/')}"
            player = f"https://w.soundcloud.com/player/?url={quote(canonical, safe='')}&auto_play=false"
            endpoint = "https://soundcloud.com/oembed"
    if not provider:
        return None
    return provider, canonical, player, f"{endpoint}?{urlencode({'url': canonical, 'format': 'json'})}"
