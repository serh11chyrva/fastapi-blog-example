"""Assemble public activity from the records that own each event."""

from datetime import datetime
from typing import Any, cast

from beanie import PydanticObjectId

from backend.feeds.cursors import FeedCursor, TimelineKind
from backend.feeds.presenters import feed_item, repost_item
from backend.feeds.repository import FeedRepository
from backend.feeds.schemas import PostFeedItem, ProfileTimelinePage
from backend.posts.models import MicroPost
from backend.profiles.models import User
from backend.profiles.repository import ProfileRepository


async def profile_timeline(user: User, cursor_text: str | None, limit: int) -> ProfileTimelinePage:
    """Merge live post, repost, and comment events without persisting copies.

    :param user: Public profile whose authorship and activity are listed.
    :param cursor_text: Opaque position from an earlier timeline page, or None.
    :param limit: Maximum number of entries to return.
    :return: Chronological public activity and its continuation position.
    """
    cursor = FeedCursor.decode(cursor_text, profile=True)

    def conditions(kind: TimelineKind, filters: dict[str, Any]) -> dict[str, Any]:
        """Combine an event source filter with the shared descending cursor.

        :param kind: Discriminator of the event source.
        :param filters: Source-specific ownership and visibility predicates.
        :return: MongoDB filter for events strictly after the cursor.
        """
        return {"$and": [filters, cursor.conditions(kind, "created_at")]} if cursor else filters

    posts = await FeedRepository.load_feed_type("micro_post", conditions("micro_post", {
        "deleted_at": None, "$or": [{"owner_id": user.id}, {"featured_author_ids": user.id}],
    }), limit)
    reposts = await FeedRepository.load_feed_type("repost", conditions("repost", {"user_id": user.id}), limit)
    events: list[tuple[datetime, TimelineKind, str, Any]] = [
        (*entry.sort_key, entry) for entry in [*posts, *reposts]
    ]
    events.sort(key=lambda event: event[:3], reverse=True)
    page = events[:limit]
    originals = [value.publication for _, _, _, value in page]
    by_id = {item.id: item for item in await ProfileRepository.users_by_ids(
        list({author_id for original in originals for author_id in original.author_ids})
    )}
    items = []
    for (_, kind, event_id, value), original in zip(page, originals, strict=True):
        if any(author_id not in by_id for author_id in original.author_ids):
            continue

        authors = [by_id[author_id] for author_id in original.author_ids]
        if kind == "repost":
            items.append(repost_item(cast(MicroPost, original), authors, value.repost, user))
        else:
            items.append(cast(PostFeedItem, feed_item(original, authors)))

    next_cursor = None
    if len(events) > limit:
        created_at, kind, event_id, _ = page[-1]
        next_cursor = FeedCursor(created_at, kind, PydanticObjectId(event_id)).encode()

    return ProfileTimelinePage(items=items, next_cursor=next_cursor)
