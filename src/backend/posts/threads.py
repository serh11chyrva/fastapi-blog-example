"""Derive automatic author threads from existing immutable reply edges."""

import base64
from collections import defaultdict
from typing import Literal, cast

from beanie import PydanticObjectId
from pydantic import AwareDatetime, BaseModel, ValidationError

from backend.core.errors import InvalidOperation, NotFound
from backend.feeds.presenters import feed_item
from backend.feeds.schemas import AuthorThreadPage, PostCard, PostFeedItem, ThreadPart, ThreadPreview
from backend.posts.context import reply_tombstone
from backend.posts.models import MicroPost
from backend.posts.visibility import visible_post_stages
from backend.profiles.repository import ProfileRepository
from backend.publications.access import readable_publication


class ThreadCursor(BaseModel):
    """Stable ascending continuation position bound to one standalone original."""

    version: Literal[1] = 1
    root: PydanticObjectId
    time: AwareDatetime
    id: PydanticObjectId


def author_thread_members(
    root: MicroPost, replies: list[MicroPost], viewer_id: PydanticObjectId | None = None,
) -> list[MicroPost]:
    """Select same-owner paths and retain deleted nodes only when connecting live parts.

    :param root: Authorized standalone original post.
    :param replies: Candidate replies, possibly including unrelated owners and branches.
    :param viewer_id: Optional owner allowed to see its archived branch.
    :return: Connected continuations in stable ascending creation-time and ID order.
    """
    children: dict[PydanticObjectId | None, list[MicroPost]] = defaultdict(list)
    for post in replies:
        context = post.reply
        if (context is not None and context.kind == "micro_post" and context.publication_id == root.id
                and post.owner_id == root.owner_id and not post.pending
                and (post.archived_at is None or post.owner_id == viewer_id)):
            children[context.parent_id].append(post)
    connected: dict[PydanticObjectId, MicroPost] = {}
    pending = list(children[None])
    while pending:
        post = pending.pop()
        if post.id in connected:
            continue
        connected[post.id] = post
        pending.extend(children[post.id])
    retained = set()
    for post in connected.values():
        if post.deleted_at is not None:
            continue
        current = post
        while current.id not in retained:
            retained.add(current.id)
            parent_id = current.reply.parent_id
            if parent_id is None:
                break
            current = connected[parent_id]
    return sorted((connected[key] for key in retained), key=lambda post: (post.created_at, str(post.id)))


async def load_author_threads(
    roots: list[MicroPost], viewer_id: PydanticObjectId | None = None,
) -> dict[PydanticObjectId, list[MicroPost]]:
    """Load candidate continuations for an entire page in one Beanie aggregation.

    :param roots: Authorized standalone originals, excluding repost wrappers.
    :param viewer_id: Optional owner for private thread reads; public feeds omit it.
    :return: Connected continuation lists keyed by original post ID.
    """
    if not roots:
        return {}
    rows = await MicroPost.aggregate([
        {"$match": {"reply.kind": "micro_post", "reply.publication_id": {"$in": [root.id for root in roots]},
                    "owner_id": {"$in": list({root.owner_id for root in roots})}}},
        *visible_post_stages(viewer_id=viewer_id),
    ]).to_list()
    by_root: dict[PydanticObjectId, list[MicroPost]] = defaultdict(list)
    for row in rows:
        post = MicroPost.model_validate(row)
        by_root[post.reply.publication_id].append(post)
    return {root.id: author_thread_members(root, by_root[root.id], viewer_id) for root in roots}


async def thread_part_cards(
    posts: list[MicroPost], read_only_ids: set[PydanticObjectId] | None = None,
) -> list[ThreadPart]:
    """Present live thread parts and content-free tombstones with one author batch.

    :param posts: Ordered parts, including deleted connectors when necessary.
    :param read_only_ids: Parts whose ancestor archive state prevents interactions.
    :return: Nonrecursive cards containing no personalized reaction flags.
    """
    ids = list({author_id for post in posts if post.deleted_at is None for author_id in post.author_ids})
    authors = {user.id: user for user in await ProfileRepository.users_by_ids(ids)} if ids else {}
    result = []
    for post in posts:
        if post.deleted_at is not None:
            result.append(reply_tombstone(post))
            continue
        if any(key not in authors for key in post.author_ids):
            raise NotFound("Author not found")
        item = feed_item(post, [authors[key] for key in post.author_ids])
        card = PostCard.model_validate(item.model_dump(exclude={"thread_preview"}))
        card.read_only = bool(read_only_ids and post.id in read_only_ids) or card.read_only
        result.append(card)
    return result


async def attach_thread_previews(cards: list[PostFeedItem], roots: list[MicroPost]) -> None:
    """Enrich standalone original cards without issuing per-card continuation reads.

    :param cards: Feed or pin cards eligible for grouping, mutated in place.
    :param roots: Corresponding public standalone original documents.
    :return: None.
    """
    eligible = {card.id for card in cards if card.reply is None}
    roots = list({root.id: root for root in roots if root.reply is None and str(root.id) in eligible}.values())
    groups = await load_author_threads(roots)
    requested = [part for members in groups.values() for part in members[:2]]
    parts = {part.id: part for part in await thread_part_cards(requested)}
    for card in cards:
        members = groups.get(PydanticObjectId(card.id), [])
        card.thread_preview = ThreadPreview(
            parts=[parts[str(post.id)] for post in members[:2]], has_more=len(members) > 2,
        ) if members else None


async def author_thread_page(
    post_id: str, cursor: str | None, limit: int, viewer_id: PydanticObjectId | None = None,
) -> AuthorThreadPage:
    """Read a standalone original and one stable page of connected author continuations.

    :param post_id: Standalone original identifier, never a reply ID.
    :param cursor: Root-bound ascending cursor, or None for the first page.
    :param limit: Maximum number of continuations in the page.
    :param viewer_id: Optional owner allowed to read archived dependencies.
    :return: The original, ordered parts, and continuation cursor when more parts exist.
    """
    root = cast(MicroPost, await readable_publication("micro_post", post_id, viewer_id))
    if root.reply is not None:
        raise NotFound("Thread original not found")
    position = None
    if cursor:
        try:
            position = ThreadCursor.model_validate_json(
                base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True),
            )
        except (ValueError, ValidationError) as exc:
            raise InvalidOperation("Invalid author-thread cursor") from exc
        if position.root != root.id:
            raise InvalidOperation("Cursor belongs to a different author thread")
    members = (await load_author_threads([root], viewer_id))[root.id]
    selected = [post for post in members if position is None
                or (post.created_at, str(post.id)) > (position.time, str(position.id))]
    page = selected[:limit]
    by_id = {post.id: post for post in members}
    read_only_ids = set()
    for post in page:
        current = post
        while True:
            if root.archived_at is not None or current.archived_at is not None:
                read_only_ids.add(post.id)
                break
            parent = current.reply.parent_id
            if parent is None:
                break
            current = by_id[parent]
    root_card = (await thread_part_cards([root]))[0]
    next_cursor = None
    if len(selected) > limit:
        last = page[-1]
        payload = ThreadCursor(root=root.id, time=last.created_at, id=last.id)
        next_cursor = base64.urlsafe_b64encode(payload.model_dump_json().encode()).decode().rstrip("=")
    return AuthorThreadPage(root=root_card, items=await thread_part_cards(page, read_only_ids), next_cursor=next_cursor)
