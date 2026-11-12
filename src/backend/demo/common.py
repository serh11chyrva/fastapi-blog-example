"""Stable fixture identities and audited insert-only persistence."""

from hashlib import sha256

from beanie import Document, PydanticObjectId

from backend.articles.models import Article
from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.core.resources import AppResources
from backend.core.transactions import transaction
from backend.posts.models import MicroPost
from backend.profiles.models import User
from backend.publications.hashtags import extract_hashtags
from backend.search.sync import sync_publication

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
    """Insert a missing fixture and its search data in one audited transaction.

    Existing canonical documents are preserved; their derived publication search data is refreshed.

    :param resources: Application infrastructure, including the transactional MongoDB client.
    :param document: Validated fixture with an explicitly assigned stable ID.
    :param actor_id: Demo account responsible for the fixture, or None for catalog records.
    :param target_type: Domain category recorded in the audit event.
    :return: True if inserted; False if the same fixture ID already exists, including deleted records.
    """
    async with transaction(resources.mongo) as session:
        existing = await type(document).get(document.id, session=session)
        if existing is not None:
            if isinstance(existing, (MicroPost, Article)):
                await sync_publication(existing, session)
            return False

        if isinstance(document, User):
            document.search_hashtags = extract_hashtags(document.display_name + "\n" + document.bio)
        await document.insert(session=session)
        if isinstance(document, (MicroPost, Article)):
            await sync_publication(document, session)
        await record_audit(
            DEMO_AUDIT, "DEMO_FIXTURE_CREATED", actor_id=actor_id,
            target_type=target_type, target_id=str(document.id), metadata={"source": "demo-v2"}, session=session,
        )

    return True
