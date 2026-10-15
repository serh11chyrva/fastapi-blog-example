"""Transport-independent metadata attached to audit events."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuditContext:
    ip_address: str | None = None
    user_agent: str | None = None
