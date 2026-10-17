from pymongo.asynchronous.client_session import AsyncClientSession

from backend.audit.models import AuditEvent


class AuditRepository:
    @staticmethod
    async def append(
        event: AuditEvent, session: AsyncClientSession | None = None
    ) -> AuditEvent:
        await event.insert(session=session)
        return event
