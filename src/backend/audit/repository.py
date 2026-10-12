from typing import Any

from backend.audit.models import AuditEvent


class AuditRepository:
    @staticmethod
    async def append(event: AuditEvent, session: Any = None) -> AuditEvent:
        await event.insert(session=session)
        return event
