"""Recipient selection boundaries and atomic notification group operations."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import DuplicateKeyError

from backend.core.errors import Conflict
from backend.core.resources import AppResources
from backend.notifications.models import LoginDetails, NotificationKind, NotificationTarget, SourceKind
from backend.notifications.repository import NotificationRepository


class NotificationService:
    """Own recipient inbox operations while source services retain their transaction ownership."""

    def __init__(self, resources: AppResources) -> None:
        """Initialize notification operations using application-owned infrastructure.

        :param resources: Application resources used for standalone inbox transactions.
        :return: None.
        """
        self.resources = resources
        self.repository = NotificationRepository()

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
