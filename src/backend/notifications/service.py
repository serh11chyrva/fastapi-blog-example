"""Recipient selection boundaries and atomic notification group operations."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import DuplicateKeyError

from backend.core.errors import Conflict
from backend.core.resources import AppResources
from backend.core.transactions import transaction
from backend.notifications.cursors import NotificationCursor
from backend.notifications.models import LoginDetails, NotificationKind, NotificationTarget, SourceKind
from backend.notifications.presenters import notification_items
from backend.notifications.repository import NotificationRepository
from backend.notifications.schemas import NotificationPage, NotificationReadRequest, NotificationSummary


class NotificationService:
    """Own recipient inbox operations while source services retain their transaction ownership."""

    def __init__(self, resources: AppResources) -> None:
        """Initialize notification operations using application-owned infrastructure.

        :param resources: Application resources used for standalone inbox transactions.
        :return: None.
        """
        self.resources = resources
        self.repository = NotificationRepository()

    async def page(self, recipient_id: PydanticObjectId, cursor: str | None, limit: int) -> NotificationPage:
        """Read current public previews inside a recipient-owned chronological inbox page.

        :param recipient_id: Authenticated account whose inbox is requested.
        :param cursor: Previous opaque timeline position, or None for the first page.
        :param limit: Validated page size from one to fifty groups.
        :return: Typed inbox rows and an opaque continuation cursor when more rows exist.
        """
        rows = await self.repository.page(recipient_id, NotificationCursor.decode(cursor), limit)
        page = rows[:limit]
        next_cursor = None
        if len(rows) > limit:
            last = page[-1]
            next_cursor = NotificationCursor(time=last.last_event_at, id=last.id).encode()
        return NotificationPage(items=await notification_items(page), next_cursor=next_cursor)

    async def summary(self, recipient_id: PydanticObjectId) -> NotificationSummary:
        """Read the recipient's current unread group count.

        :param recipient_id: Authenticated inbox owner.
        :return: Unread rows, including rows with unavailable targets.
        """
        return NotificationSummary(unread_count=await self.repository.unread_count(recipient_id))

    async def mark_read(self, recipient_id: PydanticObjectId, payload: NotificationReadRequest) -> None:
        """Commit a bounded batch of monotonic read receipts in one inbox transaction.

        :param recipient_id: Account allowed to mark only its own groups.
        :param payload: Observed versions, with duplicate group IDs combined using their maximum version.
        :return: None.
        """
        versions = {}
        for item in payload.items:
            versions[item.id] = max(versions.get(item.id, 0), item.through_version)
        async with transaction(self.resources.mongo) as session:
            await self.repository.mark_read(recipient_id, versions, session)

    async def mark_all_read(self, recipient_id: PydanticObjectId) -> None:
        """Mark the current server snapshot read, preserving the application's no-replay conflict policy.

        :param recipient_id: Authenticated inbox owner.
        :return: None.
        """
        async with transaction(self.resources.mongo) as session:
            await self.repository.mark_all_read(recipient_id, session)

    async def emit(
        self, *, recipient_id: PydanticObjectId, actor_id: PydanticObjectId | None,
        kind: NotificationKind, source_kind: SourceKind, source_id: PydanticObjectId,
        occurred_at: datetime, session: AsyncClientSession,
        target: NotificationTarget | None = None, login: LoginDetails | None = None,
    ) -> None:
        """Create a recipient event once, grouping likes and reposts by target and UTC calendar day.

        Social actions by the recipient are ignored. System logins intentionally notify
        the account itself. Uniqueness conflicts abort the caller transaction with 409.

        :param recipient_id: Account receiving the notification.
        :param actor_id: Social initiator, or None for a system event.
        :param kind: Typed notification category.
        :param source_kind: Collection category of the originating action.
        :param source_id: Originating action identifier used for deduplication and retraction.
        :param occurred_at: Aware timestamp of the originating action.
        :param session: Caller transaction including the source mutation and its audit.
        :param target: Referenced social publication, or None for a system event.
        :param login: Readable login snapshot, or None for social notifications.
        :return: None.
        """
        if kind != "login" and actor_id == recipient_id:
            return

        if kind in {"like", "repost"}:
            if target is None:
                raise ValueError("Grouped social notifications require a publication target")
            day = occurred_at.astimezone(UTC).date().isoformat()
            group_key = f"{kind}:{target.kind}:{target.id}:{day}"
        else:
            group_key = f"{source_kind}:{source_id}"

        try:
            await self.repository.append(
                recipient_id=recipient_id, actor_id=actor_id, kind=kind,
                source_kind=source_kind, source_id=source_id, group_key=group_key,
                occurred_at=occurred_at, target=target, login=login, session=session,
            )
        except DuplicateKeyError as exc:
            raise Conflict("Notifications changed; reload before retrying") from exc

    async def retract(self, source_kind: SourceKind, source_id: PydanticObjectId, session: AsyncClientSession) -> None:
        """Withdraw all recipient events for an undone source without retaining empty inbox groups.

        :param source_kind: Collection category of the undone or deleted action.
        :param source_id: Identifier of the originating interaction or comment.
        :param session: Caller transaction that also withdraws the source.
        :return: None.
        """
        await self.repository.retract(source_kind, source_id, session)
