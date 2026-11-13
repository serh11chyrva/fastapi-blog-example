"""Automatic author-thread membership, presentation, and HTTP pagination."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from backend.auth.dependencies import get_optional_user
from backend.core.resources import get_resources
from backend.feeds.presenters import feed_item
from backend.main import create_app
from backend.posts.threads import attach_thread_previews, author_thread_members


async def read_thread(root_id, cursor=None, limit=20, viewer=None):
    """Read the actual thread adapter without infrastructure connections.

    :param root_id: Standalone original identifier.
    :param cursor: Optional root-bound continuation cursor.
    :param limit: Requested page size.
    :param viewer: Optional authenticated owner.
    :return: HTTP response.
    """
    app = create_app()

    async def resources():
        """Provide an unused cache for attachment-free fixtures.

        :return: Isolated resource container.
        """
        return SimpleNamespace(redis=None)

    async def current_user():
        """Select the current test viewer.

        :return: Optional account.
        """
        return viewer

    app.dependency_overrides[get_resources] = resources
    app.dependency_overrides[get_optional_user] = current_user
    params = {"limit": limit} | ({"cursor": cursor} if cursor else {})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost:8080") as client:
        return await client.get(f"/api/v1/posts/{root_id}/thread", params=params)


def test_author_membership_combines_branches_but_stops_at_another_owner(publication_store):
    """Use owner continuity rather than root-reply IDs or discussion membership alone.

    :param publication_store: Isolated canonical documents.
    :return: None.
    """
    store = publication_store
    owner, other = store.user(), store.user()
    root = store.post(owner)
    first = store.post(owner, root)
    sibling = store.post(owner, root)
    child = store.post(owner, root, first)
    foreign = store.post(other, root, first)
    store.post(owner, root, foreign)
    other_root = store.post(other)
    store.post(owner, other_root)
    members = author_thread_members(root, list(reversed(list(store.posts.values()))))
    assert [post.id for post in members] == [first.id, sibling.id, child.id]
    assert root.id != first.reply.root_id


def test_deleted_connectors_survive_but_archived_and_pending_branches_do_not(publication_store):
    """Keep only tombstones needed by surviving same-owner continuations.

    :param publication_store: Isolated canonical documents.
    :return: None.
    """
    store = publication_store
    owner = store.user()
    root = store.post(owner)
    deleted = store.post(owner, root, deleted_at=store.now)
    child = store.post(owner, root, deleted)
    store.post(owner, root, deleted_at=store.now)
    archived = store.post(owner, root, archived_at=store.now)
    archived_child = store.post(owner, root, archived)
    pending = store.post(owner, root, pending=True)
    store.post(owner, root, pending)
    values = list(store.posts.values())
    assert [post.id for post in author_thread_members(root, values)] == [deleted.id, child.id]
    assert [post.id for post in author_thread_members(root, values, owner.id)] == [
        deleted.id, child.id, archived.id, archived_child.id,
    ]


@pytest.mark.asyncio
async def test_thread_api_paginates_equal_times_without_duplicates_and_binds_cursor(thread_store):
    """Continue ascending order across branches and reject cross-thread cursors.

    :param thread_store: Canonical documents with isolated aggregate I/O.
    :return: None.
    """
    store = thread_store
    owner = store.user()
    root = store.post(owner)
    parts = [store.post(owner, root) for _ in range(4)]
    first = await read_thread(root.id, limit=2)
    assert first.status_code == 200
    assert first.headers["cache-control"] == "private, no-store"
    assert [part["id"] for part in first.json()["items"]] == [str(post.id) for post in parts[:2]]
    cursor = first.json()["next_cursor"]
    second = await read_thread(root.id, cursor, limit=2)
    assert [part["id"] for part in second.json()["items"]] == [str(post.id) for post in parts[2:]]
    assert second.json()["next_cursor"] is None
    another = store.post(owner)
    assert (await read_thread(another.id, cursor)).status_code == 422
    assert (await read_thread(root.id, "invalid")).status_code == 422
    assert (await read_thread(parts[0].id)).status_code == 404
    assert (await read_thread(root.id, limit=0)).status_code == 422


@pytest.mark.asyncio
async def test_thread_previews_batch_roots_and_never_contain_reaction_flags(thread_store):
    """Present only two continuations while preserving original chronology.

    :param thread_store: Canonical documents with isolated aggregate I/O.
    :return: None.
    """
    store = thread_store
    owner = store.user()
    roots = [store.post(owner), store.post(owner)]
    for root in roots:
        for number in range(3):
            store.post(owner, root, created_at=store.now + timedelta(days=number + 1))
    cards = [feed_item(root, [owner]) for root in roots]
    await attach_thread_previews(cards, roots)
    assert len(store.aggregate_calls) == 1
    for card in cards:
        assert card.published_at == store.now
        assert len(card.thread_preview.parts) == 2
        assert card.thread_preview.has_more is True
        for part in card.thread_preview.parts:
            assert not {"thread_preview", "liked", "saved", "reposted"} & part.model_dump().keys()


@pytest.mark.asyncio
async def test_thread_api_preserves_tombstones_and_rechecks_visibility(thread_store):
    """Never expose erased content or inaccessible archives in a full thread.

    :param thread_store: Canonical documents with isolated aggregate I/O.
    :return: None.
    """
    store = thread_store
    owner = store.user()
    root = store.post(owner)
    deleted = store.post(owner, root, deleted_at=store.now, text="Private erased text")
    store.post(owner, root, deleted)
    archived = store.post(owner, root, archived_at=store.now)
    store.post(owner, root, archived)
    response = await read_thread(root.id)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    assert response.json()["items"][0]["kind"] == "deleted_reply"
    assert "Private erased text" not in response.text
    owner_response = await read_thread(root.id, viewer=owner)
    assert len(owner_response.json()["items"]) == 4
    assert all(post["read_only"] for post in owner_response.json()["items"][2:])
    root.archived_at = store.now
    assert (await read_thread(root.id)).status_code == 404
    root.archived_at = None
    root.deleted_at = store.now
    assert (await read_thread(root.id, viewer=owner)).status_code == 404
