"""Stable fixture identities and audited insert-only persistence."""

from hashlib import sha256

from beanie import Document, PydanticObjectId

from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.core.resources import AppResources
from backend.core.transactions import transaction

DEMO_AUDIT = AuditContext(user_agent="FastAPI Blog Example demo seed")


def demo_id(namespace: str, index: int = 0) -> PydanticObjectId:
    """Build a stable fixture ID whose sequence sorts before newly submitted comments.

    :param namespace: Feature-specific fixture namespace.
    :param index: Nonnegative sequence number within the namespace.
    :return: A deterministic ObjectId with a historical timestamp prefix.
    """
    return PydanticObjectId(f"64656d6f{sha256(namespace.encode()).hexdigest()[:8]}{index:08x}")


async def insert_fixture(
    resources: AppResources, document: Document, actor_id: PydanticObjectId | None, target_type: str,
) -> bool:
    """Insert a missing fixture and its audit event in one transaction, preserving existing documents.

    :param resources: Application infrastructure, including the transactional MongoDB client.
    :param document: Validated fixture with an explicitly assigned stable ID.
    :param actor_id: Demo account responsible for the fixture, or None for catalog records.
    :param target_type: Domain category recorded in the audit event.
    :return: True if inserted; False if the same fixture ID already exists, including deleted records.
    """
    async with transaction(resources.mongo) as session:
        if await type(document).get(document.id, session=session) is not None:
            return False

        await document.insert(session=session)
        await record_audit(
            DEMO_AUDIT, "DEMO_FIXTURE_CREATED", actor_id=actor_id,
            target_type=target_type, target_id=str(document.id), metadata={"source": "demo-v2"}, session=session,
        )

    return True
