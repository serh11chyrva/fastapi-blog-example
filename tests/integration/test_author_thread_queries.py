"""Real MongoDB query checks in a fresh disposable database, explicitly enabled."""

from datetime import UTC, datetime, timedelta
from os import environ
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from beanie import PydanticObjectId, init_beanie
from pymongo import AsyncMongoClient

from backend.articles.models import Article
from backend.core.config import get_settings
from backend.feeds.service import current_cached_feed, make_feed
from backend.interactions.models import PublicationInteraction
from backend.posts.context import post_context
from backend.posts.models import MicroPost, ReplyMetadata
from backend.posts.threads import author_thread_page
from backend.profiles.models import User
from backend.profiles.timeline import profile_timeline
from backend.publications.service import PublicationStateService


@pytest_asyncio.fixture
async def mongo_store():
    """Provision and remove only a uniquely named integration-test database.

    :return: Async factories backed by the isolated database.
    """
    if environ.get("RUN_MONGODB_TESTS") != "1":
        pytest.skip("Set RUN_MONGODB_TESTS=1 and MONGODB_URL to enable isolated MongoDB integration checks")
    settings = get_settings()
    database_name = f"codex_thread_{uuid4().hex[:20]}"
    client = AsyncMongoClient(settings.mongodb_url, tz_aware=True, serverSelectionTimeoutMS=15000)
    now = datetime(2026, 11, 13, tzinfo=UTC)

    async def user():
        """Insert a unique account into the disposable database.

        :return: Persisted account.
        """
        name = f"writer_{uuid4().hex}"
        return await User(email=f"{name}@example.com", username=name, display_name="Test writer",
                          created_at=now, updated_at=now).insert()

    async def post(owner, original=None, parent=None, **changes):
        """Insert a post or reply using canonical immutable metadata.

        :param owner: Account owning the new post.
        :param original: Optional standalone original.
        :param parent: Optional immediate parent reply.
        :param changes: Field overrides for the scenario.
        :return: Persisted post.
        """
        value = MicroPost(owner_id=owner.id, text="Integration fixture", created_at=now, updated_at=now)
        if original is not None:
            value.id = PydanticObjectId()
            value.reply = ReplyMetadata(
                kind="micro_post", publication_id=original.id, parent_id=parent.id if parent else None,
                root_id=parent.reply.root_id if parent else value.id, depth=parent.reply.depth + 1 if parent else 0,
            )
        for key, replacement in changes.items():
            setattr(value, key, replacement)
        return await value.insert()

    try:
        await init_beanie(database=client[database_name], document_models=[User, MicroPost, Article, PublicationInteraction])
        yield SimpleNamespace(user=user, post=post, now=now)
    finally:
        try:
            if (database_name.startswith("codex_thread_") and len(database_name) == len("codex_thread_") + 20
                    and database_name != settings.mongodb_database):
                await client.drop_database(database_name)
        finally:
            await client.close()


@pytest.mark.asyncio
async def test_profile_groups_before_pagination_and_retains_foreign_branches(mongo_store):
    """A small page counts complete thread roots instead of hidden continuation rows.

    :param mongo_store: Isolated MongoDB document factories.
    :return: None.
    """
    store = mongo_store
    owner, other = await store.user(), await store.user()
    older = await store.post(owner, created_at=store.now - timedelta(days=3))
    root = await store.post(owner, created_at=store.now - timedelta(days=2))
    first = await store.post(owner, root)
    for number in range(5):
        await store.post(owner, root, first, created_at=store.now + timedelta(minutes=number + 1))
    foreign = await store.post(other, root, first)
    independent = await store.post(owner, root, foreign, created_at=store.now + timedelta(minutes=10))
    await PublicationInteraction(publication_kind="micro_post", publication_id=root.id, user_id=owner.id,
                                 action="repost", created_at=store.now + timedelta(minutes=20)).insert()
    cursor = None
    seen = []
    for _ in range(5):
        page = await profile_timeline(owner, cursor, 1)
        seen.extend((item.kind, item.id) for item in page.items)
        cursor = page.next_cursor
        if cursor is None:
            break
    assert [kind for kind, _ in seen] == ["repost", "micro_post", "micro_post", "micro_post"]
    assert [key for kind, key in seen if kind == "micro_post"] == [str(independent.id), str(root.id), str(older.id)]
    page = await profile_timeline(owner, None, 20)
    card = next(item for item in page.items if item.id == str(root.id))
    assert len(card.thread_preview.parts) == 2
    assert card.thread_preview.has_more is True


@pytest.mark.asyncio
async def test_profile_keeps_credited_continuation_when_original_is_not_credited(mongo_store):
    """Only group a continuation when the same profile can display its original.

    :param mongo_store: Isolated MongoDB document factories.
    :return: None.
    """
    owner, featured = await mongo_store.user(), await mongo_store.user()
    root = await mongo_store.post(owner)
    child = await mongo_store.post(owner, root, featured_author_ids=[featured.id])
    page = await profile_timeline(featured, None, 1)
    assert [item.id for item in page.items] == [str(child.id)]
    root.featured_author_ids = [featured.id]
    await root.save()
    page = await profile_timeline(featured, None, 1)
    assert [item.id for item in page.items] == [str(root.id)]
    assert page.next_cursor is None
    assert page.items[0].thread_preview.parts[0].id == str(child.id)


@pytest.mark.asyncio
async def test_cached_preview_rechecks_archives_deletions_and_current_content(mongo_store):
    """Rebuild nested previews even when invalidation did not remove a cached page.

    :param mongo_store: Isolated MongoDB document factories.
    :return: None.
    """
    owner = await mongo_store.user()
    root = await mongo_store.post(owner)
    first = await mongo_store.post(owner, root)
    child = await mongo_store.post(owner, root, first)
    sibling = await mongo_store.post(owner, root)
    page = await make_feed(SimpleNamespace(redis=None), None, "micro_post", None, 20)
    assert [part.id for part in page.items[0].thread_preview.parts] == [str(first.id), str(child.id)]
    first.archived_at = mongo_store.now
    await first.save()
    refreshed = await current_cached_feed(page)
    assert [part.id for part in refreshed.items[0].thread_preview.parts] == [str(sibling.id)]
    first.archived_at = None
    first.deleted_at = mongo_store.now
    first.text = ""
    await first.save()
    child.text = "Latest child content"
    await child.save()
    refreshed = await current_cached_feed(page)
    parts = refreshed.items[0].thread_preview.parts
    assert parts[0].kind == "deleted_reply"
    assert parts[1].text == "Latest child content"
    context = await post_context(str(child.id))
    assert context.ancestors[0].kind == "deleted_reply"
    thread = await author_thread_page(str(root.id), None, 1)
    next_page = await author_thread_page(str(root.id), thread.next_cursor, 1)
    assert thread.items[0].kind == "deleted_reply"
    assert next_page.items[0].id == str(child.id)


@pytest.mark.asyncio
async def test_pins_and_following_keep_explicit_events_independent(mongo_store):
    """Pinned continuations and reposts remain explicit while originals carry previews.

    :param mongo_store: Isolated MongoDB document factories.
    :return: None.
    """
    store = mongo_store
    owner, other = await store.user(), await store.user()
    root = await store.post(owner, pinned_at=store.now)
    continuation = await store.post(owner, root, pinned_at=store.now)
    outside = await store.post(other)
    await PublicationInteraction(publication_kind="micro_post", publication_id=outside.id, user_id=owner.id,
                                 action="repost", created_at=store.now + timedelta(minutes=1)).insert()
    page = await make_feed(SimpleNamespace(redis=None), [owner.id], "micro_post", None, 20)
    assert len(page.items) == 2
    original = next(item for item in page.items if item.kind == "micro_post")
    repost = next(item for item in page.items if item.kind == "repost")
    assert original.thread_preview.parts[0].id == str(continuation.id)
    assert repost.post.id == str(outside.id)
    assert repost.post.thread_preview is None
    pins = await PublicationStateService(SimpleNamespace(redis=None), None).pins(owner.id)
    assert {item.id for item in pins} == {str(root.id), str(continuation.id)}
    assert next(item for item in pins if item.id == str(root.id)).thread_preview is not None
    assert next(item for item in pins if item.id == str(continuation.id)).thread_preview is None
