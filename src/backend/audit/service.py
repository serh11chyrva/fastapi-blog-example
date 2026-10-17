"""Append audit events in the same transaction as the application operation."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from pydantic import JsonValue
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.audit.context import AuditContext
from backend.audit.models import AuditEvent
from backend.audit.repository import AuditRepository


async def record_audit(
    context: AuditContext,
    action: str,
    *,
    actor_id: PydanticObjectId | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict[str, JsonValue] | None = None,
    session: AsyncClientSession | None = None,
) -> AuditEvent:
    """Persist an append-only audit event in the supplied transaction.

    :param context: Actor-independent request metadata for audit and session records.
    :param action: Audit action identifying the operation being recorded.
    :param actor_id: Account ID responsible for the event, if known.
    :param target_type: Domain resource type affected by the event.
    :param target_id: Identifier of the resource targeted by the operation.
    :param metadata: Additional structured details stored with the audit event.
    :param session: Optional MongoDB session for the operation or caller transaction.
    :return: The persisted audit event.
    """
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        occurred_at=datetime.now(UTC),
        ip_address=context.ip_address,
        user_agent=context.user_agent,
        metadata=metadata or {},
    )

    return await AuditRepository.append(event, session=session)
