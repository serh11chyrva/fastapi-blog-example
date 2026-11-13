"""Owner-scoped notification inbox, unread summary, and version-aware read receipts."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from backend.api.metadata import Origin, documented_responses
from backend.auth.dependencies import CurrentUser
from backend.core.resources import Resources
from backend.notifications.schemas import NotificationPage, NotificationReadRequest, NotificationSummary
from backend.notifications.service import NotificationService

router = APIRouter(prefix="/me/notifications", tags=["Notifications"])
PRIVATE_HEADERS = {"Cache-Control": "private, no-store"}


def get_notification_service(resources: Resources) -> NotificationService:
    """Create the request-scoped notification service.

    :param resources: Application-owned MongoDB and other infrastructure clients.
    :return: The configured notification service.
    """
    return NotificationService(resources)


Notifications = Annotated[NotificationService, Depends(get_notification_service)]
InboxCursor = Annotated[str | None, Query(max_length=512, description="Opaque next_cursor from the preceding page.")]
InboxLimit = Annotated[int, Query(ge=1, le=50, description="Inbox rows per page; defaults to 20, maximum 50.")]


@router.get(
    "", response_model=NotificationPage, summary="List your notification inbox",
    description=(
        "Returns only your rows, newest surviving event time and group ID first. Likes and reposts group by "
        "publication and UTC calendar day. Unavailable targets remain as content-free placeholders and count "
        "toward the unread total. Public actors and previews are resolved on every read. Opening this endpoint "
        "does not mark rows read. Groups can move between pages after activity; deduplicate by row ID and "
        "restart pagination when refreshing. Responses are private and never cached."
    ),
    responses=documented_responses(401, 422, 503),
)
async def list_notifications(
    current_user: CurrentUser, notifications: Notifications, response: Response,
    cursor: InboxCursor = None, limit: InboxLimit = 20,
) -> NotificationPage:
    """Read the authenticated account's private inbox without changing read state.

    :param current_user: Account resolved from the current session cookie.
    :param notifications: Request-scoped inbox service.
    :param response: Response receiving private no-store cache headers.
    :param cursor: Previous opaque position, or None for the first page.
    :param limit: Validated bounded row count.
    :return: Typed notification groups and a continuation cursor.
    """
    response.headers.update(PRIVATE_HEADERS)
    return await notifications.page(current_user.id, cursor, limit)


@router.get(
    "/summary", response_model=NotificationSummary, summary="Count your unread notification rows",
    description="Counts unread rows, including unavailable targets. Several likes in one group count as one row.",
    responses=documented_responses(401, 503),
)
async def notification_summary(
    current_user: CurrentUser, notifications: Notifications, response: Response,
) -> NotificationSummary:
    """Read the current account's unread row count.

    :param current_user: Account resolved from the session cookie.
    :param notifications: Request-scoped inbox service.
    :param response: Response receiving private no-store cache headers.
    :return: The current unread group count.
    """
    response.headers.update(PRIVATE_HEADERS)
    return await notifications.summary(current_user.id)


@router.put(
    "/read", status_code=204, summary="Mark viewed notification versions read",
    description=(
        "Accepts one to fifty observed group versions. Advances only your own read boundaries, never beyond "
        "issued events. Newer events remain unread; repeated receipts are no-ops. Missing or foreign IDs are "
        "ignored. The batch commits atomically; conflicts return 409 and require reconciliation before retrying."
    ),
    responses=documented_responses(401, 403, 409, 422, 503),
)
async def read_notifications(
    _origin: Origin, payload: NotificationReadRequest, current_user: CurrentUser, notifications: Notifications,
) -> Response:
    """Commit version-bounded read receipts for the current account only.

    :param _origin: Validated same-origin mutation header.
    :param payload: Bounded batch of observed group versions.
    :param current_user: Account owning the inbox.
    :param notifications: Request-scoped inbox service.
    :return: An empty private no-store response after the batch commits.
    """
    await notifications.mark_read(current_user.id, payload)
    return Response(status_code=204, headers=PRIVATE_HEADERS)


@router.put(
    "/read-all", status_code=204, summary="Mark your current inbox snapshot read",
    description=(
        "No request body. Marks the transaction's existing unread groups read. Later groups stay unread; "
        "concurrent updates to selected groups can return 409. Reconcile and explicitly request again rather "
        "than automatically replaying a failed operation. Responses are private and never cached."
    ),
    responses=documented_responses(401, 403, 409, 503),
)
async def read_all_notifications(
    _origin: Origin, current_user: CurrentUser, notifications: Notifications,
) -> Response:
    """Mark a server snapshot of the current account's inbox read atomically.

    :param _origin: Validated same-origin mutation header.
    :param current_user: Account owning the selected inbox.
    :param notifications: Request-scoped inbox service.
    :return: An empty private no-store response after the snapshot mutation commits.
    """
    await notifications.mark_all_read(current_user.id)
    return Response(status_code=204, headers=PRIVATE_HEADERS)
