"""Client categories persisted when a session is created."""

from enum import StrEnum


class ClientType(StrEnum):
    """Supported client categories recorded on authentication sessions."""

    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
