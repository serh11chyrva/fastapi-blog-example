"""Conversation API behavior using isolated canonical documents."""

from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from backend.auth.dependencies import get_optional_user
from backend.core.resources import get_resources
from backend.main import create_app


async def read_context(post_id, viewer=None):
    """Read the actual HTTP adapter without infrastructure connections.

    :param post_id: Selected resource identifier.
    :param viewer: Optional authenticated owner.
    :return: The HTTP response.
    """
    app = create_app()

    async def resources():
        """Provide unused cache infrastructure for attachment-free fixtures.

        :return: Resource container with no external connection.
        """
        return SimpleNamespace(redis=None)

    async def current_user():
        """Provide the selected test viewer.

        :return: Optional authenticated account.
        """
        return viewer

    app.dependency_overrides[get_resources] = resources
    app.dependency_overrides[get_optional_user] = current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost:8080") as client:
        return await client.get(f"/api/v1/posts/{post_id}/context")


@pytest.mark.asyncio
async def test_context_returns_only_ordered_ancestors_and_erases_deleted_content(publication_store):
    """Keep navigation through deleted ancestors without exposing sibling branches.

    :param publication_store: Isolated canonical documents.
    :return: None.
    """
    store = publication_store
    owner = store.user()
    root = store.post(owner)
    first = store.post(owner, root)
    deleted = store.post(owner, root, first, text="Must never leak", deleted_at=store.now)
    selected = store.post(owner, root, deleted)
    store.post(owner, root, first, text="Sibling")
    response = await read_context(selected.id)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    value = response.json()
    assert value["original"]["id"] == str(root.id)
    assert [item["id"] for item in value["ancestors"]] == [str(first.id), str(deleted.id)]
    assert value["ancestors"][1]["kind"] == "deleted_reply"
    assert "Must never leak" not in response.text
    assert "Sibling" not in response.text
    assert not {"text", "authors", "attachments", "owner_id"} & value["ancestors"][1].keys()
    tombstone = await read_context(deleted.id)
    assert tombstone.status_code == 200
    assert tombstone.json()["post"]["kind"] == "deleted_reply"


@pytest.mark.asyncio
async def test_context_supports_standalone_posts_and_article_roots(publication_store):
    """Keep standalone paths empty and article contexts compact.

    :param publication_store: Isolated canonical documents.
    :return: None.
    """
    store = publication_store
    owner = store.user()
    root = store.post(owner)
    response = await read_context(root.id)
    assert response.status_code == 200
    assert response.json()["original"] is None
    assert response.json()["ancestors"] == []
    article = store.article(owner)
    comment = store.post(owner, article)
    response = await read_context(comment.id)
    assert response.status_code == 200
    assert response.json()["original"]["kind"] == "article"
    assert "body" not in response.json()["original"]


@pytest.mark.asyncio
@pytest.mark.parametrize("hidden", ["deleted_at", "archived_at", "pending"])
async def test_context_hides_unavailable_originals(publication_store, hidden):
    """Hide reply paths whose original is no longer public.

    :param publication_store: Isolated canonical documents.
    :param hidden: Original visibility field changed in this case.
    :return: None.
    """
    store = publication_store
    owner = store.user()
    root = store.post(owner, **{hidden: True if hidden == "pending" else store.now})
    selected = store.post(owner, root)
    assert (await read_context(selected.id)).status_code == 404


@pytest.mark.asyncio
async def test_context_enforces_each_archive_owner_and_inherits_read_only(publication_store):
    """Owner access never grants access to somebody else's archived ancestor.

    :param publication_store: Isolated canonical documents.
    :return: None.
    """
    store = publication_store
    owner, other = store.user(), store.user()
    root = store.post(owner)
    archived = store.post(owner, root, archived_at=store.now)
    selected = store.post(other, root, archived)
    assert (await read_context(selected.id)).status_code == 404
    assert (await read_context(selected.id, other)).status_code == 404
    response = await read_context(selected.id, owner)
    assert response.status_code == 200
    assert response.json()["post"]["read_only"] is True


@pytest.mark.asyncio
async def test_context_rejects_broken_cycles_and_malformed_ids(publication_store):
    """Fail closed on invalid or corrupted path membership.

    :param publication_store: Isolated canonical documents.
    :return: None.
    """
    store = publication_store
    owner = store.user()
    root = store.post(owner)
    selected = store.post(owner, root)
    selected.reply.parent_id = selected.id
    assert (await read_context(selected.id)).status_code == 404
    assert (await read_context("invalid")).status_code == 404
    selected.reply.parent_id = None
    root.deleted_at = store.now
    assert (await read_context(root.id)).status_code == 404
