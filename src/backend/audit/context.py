"""Transport-independent metadata attached to audit events."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuditContext:
    """Immutable request metadata shared by audited application operations."""

    ip_address: str | None = None
    user_agent: str | None = None
