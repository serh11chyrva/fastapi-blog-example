from enum import StrEnum
from urllib.parse import urlsplit


class LinkPlatform(StrEnum):
    """Recognized destination platforms for public profile links."""

    WEBSITE = "website"
    GITHUB = "github"
    GITLAB = "gitlab"
    X = "x"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    THREADS = "threads"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    REDDIT = "reddit"
    TWITCH = "twitch"
    MEDIUM = "medium"
    SUBSTACK = "substack"
    PINTEREST = "pinterest"
    SOUNDCLOUD = "soundcloud"
    BANDCAMP = "bandcamp"
    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"
    BEHANCE = "behance"
    ITCH_IO = "itch_io"
    KICK = "kick"
    ARTSTATION = "artstation"
    DRIBBBLE = "dribbble"
    DEVIANTART = "deviantart"
    VIMEO = "vimeo"
    PATREON = "patreon"
    KO_FI = "ko_fi"


PLATFORM_DOMAINS = {
    LinkPlatform.GITHUB: ("github.com",),
    LinkPlatform.GITLAB: ("gitlab.com",),
    LinkPlatform.X: ("x.com", "twitter.com"),
    LinkPlatform.FACEBOOK: ("facebook.com", "fb.com", "fb.me"),
    LinkPlatform.INSTAGRAM: ("instagram.com",),
    LinkPlatform.THREADS: ("threads.net", "threads.com"),
    LinkPlatform.LINKEDIN: ("linkedin.com", "lnkd.in"),
    LinkPlatform.YOUTUBE: ("youtube.com", "youtu.be"),
    LinkPlatform.TIKTOK: ("tiktok.com",),
    LinkPlatform.TELEGRAM: ("t.me", "telegram.me", "telegram.org"),
    LinkPlatform.DISCORD: ("discord.com", "discord.gg"),
    LinkPlatform.REDDIT: ("reddit.com", "redd.it"),
    LinkPlatform.TWITCH: ("twitch.tv",),
    LinkPlatform.MEDIUM: ("medium.com",),
    LinkPlatform.SUBSTACK: ("substack.com",),
    LinkPlatform.PINTEREST: ("pinterest.com", "pin.it"),
    LinkPlatform.SOUNDCLOUD: ("soundcloud.com",),
    LinkPlatform.BANDCAMP: ("bandcamp.com",),
    LinkPlatform.SPOTIFY: ("spotify.com", "spotify.link"),
    LinkPlatform.APPLE_MUSIC: ("music.apple.com",),
    LinkPlatform.BEHANCE: ("behance.net",),
    LinkPlatform.ITCH_IO: ("itch.io",),
    LinkPlatform.KICK: ("kick.com",),
    LinkPlatform.ARTSTATION: ("artstation.com",),
    LinkPlatform.DRIBBBLE: ("dribbble.com",),
    LinkPlatform.DEVIANTART: ("deviantart.com",),
    LinkPlatform.VIMEO: ("vimeo.com",),
    LinkPlatform.PATREON: ("patreon.com",),
    LinkPlatform.KO_FI: ("ko-fi.com",),
}


def validate_link_url(value: str) -> str:
    """Accept absolute HTTP(S) URLs safe to use in a Location header.

    :param value: Absolute HTTP or HTTPS destination without credentials.
    :return: The validated HTTP or HTTPS destination URL.
    """
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in value) or "\\" in value:
        raise ValueError("Links cannot contain whitespace, control characters, or backslashes")

    try:
        parsed = urlsplit(value)
        _ = parsed.port
        hostname = parsed.hostname
    except ValueError as exc:
        raise ValueError("Links must use a valid http or https URL") from exc

    if (
        parsed.scheme not in {"https", "http"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("Links must use an http or https URL with a hostname and no credentials")

    return value


def detect_platform(url: str) -> LinkPlatform:
    """Match hostnames at domain boundaries, never URL paths or query strings.

    :param url: HTTP or HTTPS destination URL to inspect.
    :return: The recognized link platform or the generic fallback.
    """
    hostname = (urlsplit(url).hostname or "").lower().rstrip(".")

    for platform, domains in PLATFORM_DOMAINS.items():
        if any(hostname == domain or hostname.endswith(f".{domain}") for domain in domains):
            return platform

    return LinkPlatform.WEBSITE
