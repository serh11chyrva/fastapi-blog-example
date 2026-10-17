from pymongo.asynchronous.client_session import AsyncClientSession

from backend.audit.models import AuditEvent


class AuditRepository:
    """Persistence operations for append-only audit events."""

    @staticmethod
    async def append(event: AuditEvent, session: AsyncClientSession | None = None) -> AuditEvent:
        """Append an audit event in the supplied database session.

        :param event: Audit event to append without modifying earlier records.
        :param session: Optional MongoDB session for the operation or caller
            transaction.
        :return: The inserted audit event.
        """
        await event.insert(session=session)

        return event
