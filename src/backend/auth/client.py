"""Client categories persisted when a session is created."""

from enum import StrEnum


class ClientType(StrEnum):
    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
