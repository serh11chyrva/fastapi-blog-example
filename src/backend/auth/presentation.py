"""Human-readable session metadata without exposing raw IP addresses or User-Agents."""

from ipaddress import ip_address

from geoip2.database import Reader
from geoip2.errors import AddressNotFoundError
from loguru import logger
from maxminddb import InvalidDatabaseError
from user_agents import parse

from backend.auth.client import ClientType
from backend.auth.models import AuthSession
from backend.auth.schemas import SessionResponse


def open_geoip_database(path: str) -> Reader | None:
    """Keep authentication available when the optional location database is unavailable.

    :param path: Filesystem path to the local GeoIP City database.
    :return: The GeoIP reader, or None if the database cannot be opened.
    """
    try:
        return Reader(path)
    except (OSError, ValueError, InvalidDatabaseError):
        logger.warning("GeoLite2 City database is unavailable; session locations will be unknown")

        return None


def format_location(address: str | None, reader: Reader | None) -> str:
    """Format an approximate city and country using the GeoIP database.

    :param address: Client IP address to resolve to an approximate location.
    :param reader: Opened GeoIP reader, or None when location lookup is unavailable.
    :return: A readable location label, falling back to Unknown location.
    """
    if not address or reader is None:
        return "Unknown location"

    try:
        parsed_address = ip_address(address)

        if not parsed_address.is_global:
            return "Unknown location"

        location = reader.city(str(parsed_address))
        parts = [
            location.city.name,
            location.subdivisions.most_specific.name,
            location.country.name,
        ]

        return ", ".join(dict.fromkeys(part for part in parts if part)) or "Unknown location"
    except (AddressNotFoundError, ValueError):
        return "Unknown location"
    except (OSError, InvalidDatabaseError):
        logger.warning("GeoLite2 City lookup failed; session location will be unknown")

        return "Unknown location"


def format_device(session: AuthSession) -> str:
    """Format a session's browser, operating system, or native device label.

    :param session: Authentication session whose client metadata is formatted.
    :return: The readable device label for the session client type.
    """
    agent = parse((session.user_agent or "")[:512])
    operating_system = agent.get_os() if agent.os.family != "Other" else None

    if session.client_type == ClientType.WEB:
        browser = agent.get_browser() if agent.browser.family != "Other" else "Unknown browser"

        return f"{browser} on {operating_system}" if operating_system else browser

    device = session.device_name

    if not device and agent.device.family != "Other":
        device = agent.get_device()

    if device and operating_system and device != operating_system:
        return f"{device} · {operating_system}"

    return device or operating_system or "Unknown device"


def present_sessions(sessions: list[AuthSession], current_id: str, reader: Reader | None) -> list[SessionResponse]:
    """Resolve locations off the event loop using the application-owned database reader.

    :param sessions: Session documents to present without exposing raw request metadata.
    :param current_id: Identifier of the session used for the current request.
    :param reader: Opened GeoIP reader, or None when location lookup is unavailable.
    :return: Session responses with readable labels and a current-session flag.
    """
    return [
        SessionResponse(
            id=str(session.id),
            created_at=session.created_at,
            last_seen_at=session.last_seen_at,
            expires_at=session.expires_at,
            client_type=session.client_type,
            location=format_location(session.ip_address, reader),
            device=format_device(session),
            current=str(session.id) == current_id,
        )
        for session in sessions
    ]
