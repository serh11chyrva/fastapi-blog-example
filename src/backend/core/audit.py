from datetime import UTC, datetime
from typing import Any

from beanie import PydanticObjectId
from fastapi import Request
from backend.audit.models import AuditEvent
from backend.audit.repository import AuditRepository


def request_details(request: Request) -> tuple[str | None, str | None]:
    # Nginx overwrites X-Real-IP and is the only service exposed to the host.
    ip_address = request.headers.get("x-real-ip") or (request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent", "")[:512] or None
    return ip_address, user_agent


async def record_audit(
    request: Request,
    action: str,
    *,
    actor_id: PydanticObjectId | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    session: Any = None,
) -> AuditEvent:
    ip_address, user_agent = request_details(request)
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        occurred_at=datetime.now(UTC),
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {},
    )
    return await AuditRepository.append(event, session=session)
