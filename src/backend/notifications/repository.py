"""Transactional Beanie persistence for notification membership and inbox projections."""

from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.notifications.cursors import NotificationCursor
from backend.notifications.models import (
    LoginDetails, NotificationEvent, NotificationGroup, NotificationKind, NotificationTarget, SourceKind,
)


class NotificationRepository:
    """Maintain source events and their grouped recipient projections in caller transactions."""

    @staticmethod
    async def page(
        recipient_id: PydanticObjectId, cursor: NotificationCursor | None, limit: int,
    ) -> list[NotificationGroup]:
        """Read a bounded descending inbox page owned by one account.

        :param recipient_id: Account whose private inbox is requested.
        :param cursor: Previous timeline position, or None for the first page.
        :param limit: Page size; one additional group detects continuation.
        :return: At most limit plus one groups, including rows with unavailable content.
        """
        conditions: dict[str, Any] = {"recipient_id": recipient_id}
        if cursor is not None:
            conditions.update(cursor.conditions())
        return await NotificationGroup.find(conditions).sort(
            ("last_event_at", -1), ("_id", -1),
        ).limit(limit + 1).to_list()

    @staticmethod
    async def unread_count(recipient_id: PydanticObjectId) -> int:
        """Count unread rows without resolving potentially unavailable targets.

        :param recipient_id: Account owning the private inbox.
        :return: The number of unread groups, counting each grouped row once.
        """
        return await NotificationGroup.find({"recipient_id": recipient_id, "is_read": False}).count()

    @staticmethod
    async def mark_read(
        recipient_id: PydanticObjectId, versions: dict[PydanticObjectId, int], session: AsyncClientSession,
    ) -> None:
        """Advance owned read boundaries without consuming events newer than the observed versions.

        :param recipient_id: Account allowed to change only its own inbox receipts.
        :param versions: Group identifiers mapped to their highest observed event sequence.
        :param session: Inbox mutation transaction; concurrent group changes can abort it with 409.
        :return: None; missing and foreign group IDs are ignored without revealing their existence.
        """
        groups = await NotificationGroup.find({
            "recipient_id": recipient_id, "_id": {"$in": list(versions)},
        }, session=session).to_list()
        for group in groups:
            boundary = max(group.read_through_sequence, min(versions[group.id], group.sequence))
            if boundary == group.read_through_sequence:
                continue
            group.read_through_sequence = boundary
            group.is_read = group.latest_sequence <= boundary
            await group.replace(session=session)

    @staticmethod
    async def mark_all_read(recipient_id: PydanticObjectId, session: AsyncClientSession) -> None:
        """Mark the transaction's current unread group snapshot without replaying after a conflict.

        :param recipient_id: Account owning the inbox; other recipients are never selected.
        :param session: Snapshot transaction that excludes later inserts and conflicts with concurrent row updates.
        :return: None.
        """
        await NotificationGroup.find({"recipient_id": recipient_id, "is_read": False}, session=session).update_many(
            [{"$set": {"is_read": True, "read_through_sequence": "$sequence"}}], session=session,
        )

    @staticmethod
    async def append(
        *, recipient_id: PydanticObjectId, actor_id: PydanticObjectId | None,
        kind: NotificationKind, source_kind: SourceKind, source_id: PydanticObjectId,
        group_key: str, occurred_at: datetime, target: NotificationTarget | None,
        login: LoginDetails | None, session: AsyncClientSession,
    ) -> None:
        """Insert a source once and advance its group's sequence without resetting prior read receipts.

        :param recipient_id: Account owning the resulting inbox row.
        :param actor_id: Public account responsible for a social event, or None for a system event.
        :param kind: Typed notification category.
        :param source_kind: Collection category of the originating action.
        :param source_id: Identifier of the originating action.
        :param group_key: Recipient-local grouping key, including the UTC day for grouped actions.
        :param occurred_at: Time of the originating action.
        :param target: Publication reference for social events, or None for system events.
        :param login: Immutable readable login details, or None for social events.
        :param session: Caller transaction committing the source action and notification together.
        :return: None.
        """
        existing = await NotificationEvent.find_one({
            "source_kind": source_kind, "source_id": source_id, "recipient_id": recipient_id,
        }, session=session)
        if existing is not None:
            return

        group = await NotificationGroup.find_one({
            "recipient_id": recipient_id, "group_key": group_key,
        }, session=session)
        new_group = group is None
        if group is None:
            group = NotificationGroup(
                id=PydanticObjectId(), recipient_id=recipient_id, group_key=group_key,
                kind=kind, target=target, login=login, last_event_at=occurred_at,
            )

        group.sequence += 1
        group.latest_sequence = group.sequence
        group.event_count += 1
        group.last_event_at = occurred_at
        group.is_read = False
        if actor_id is not None:
            group.actor_ids = [actor_id, *[key for key in group.actor_ids if key != actor_id]][:3]

        await NotificationEvent(
            recipient_id=recipient_id, group_id=group.id, actor_id=actor_id,
            source_kind=source_kind, source_id=source_id, sequence=group.sequence, occurred_at=occurred_at,
        ).insert(session=session)
        if new_group:
            await group.insert(session=session)
        else:
            await group.replace(session=session)

    @staticmethod
    async def retract(source_kind: SourceKind, source_id: PydanticObjectId, session: AsyncClientSession) -> None:
        """Remove source membership and reconstruct affected groups while preserving their sequence counters.

        :param source_kind: Collection category of the undone or deleted action.
        :param source_id: Identifier of the action whose notifications must disappear.
        :param session: Caller transaction also undoing or deleting the source action.
        :return: None.
        """
        events = await NotificationEvent.find({
            "source_kind": source_kind, "source_id": source_id,
        }, session=session).to_list()
        for event in events:
            await event.delete(session=session)
            group = await NotificationGroup.get(event.group_id, session=session)
            if group is None:
                continue

            remaining = await NotificationEvent.find({"group_id": group.id}, session=session).sort(
                ("sequence", -1),
            ).limit(3).to_list()
            if not remaining:
                await group.delete(session=session)
                continue

            group.event_count -= 1
            group.latest_sequence = remaining[0].sequence
            group.last_event_at = remaining[0].occurred_at
            group.actor_ids = list(dict.fromkeys(row.actor_id for row in remaining if row.actor_id is not None))
            group.is_read = group.latest_sequence <= group.read_through_sequence
            await group.replace(session=session)
