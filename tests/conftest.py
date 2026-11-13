"""Isolated publication documents with persistence boundaries replaced in memory."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from beanie import PydanticObjectId

from backend.articles.models import Article
from backend.posts.models import MicroPost, ReplyMetadata
from backend.profiles.models import User
from backend.profiles.repository import ProfileRepository


@pytest.fixture
def publication_store(monkeypatch):
    """Provide canonical documents without connecting to the development database.

    :param monkeypatch: Pytest restoration of repository boundaries.
    :return: Isolated document factories and storage maps.
    """
    posts, articles, users = {}, {}, {}
    now = datetime(2026, 11, 13, tzinfo=UTC)

    def user():
        """Create an isolated public account.

        :return: The stored account document.
        """
        key = PydanticObjectId()
        value = User.model_construct(id=key, email=f"{key}@example.com", username=f"u{key}",
                                     display_name="Writer", created_at=now, updated_at=now)
        users[key] = value
        return value

    def post(owner, original=None, parent=None, **changes):
        """Create a post with the real immutable reply metadata conventions.

        :param owner: Account owning the publication.
        :param original: Optional standalone post or article discussion root.
        :param parent: Optional immediate parent reply.
        :param changes: Field overrides for visibility and ordering scenarios.
        :return: The stored post document.
        """
        key = changes.pop("id", PydanticObjectId())
        reply = ReplyMetadata(
            kind="article" if isinstance(original, Article) else "micro_post",
            publication_id=original.id, parent_id=parent.id if parent else None,
            root_id=parent.reply.root_id if parent else key, depth=parent.reply.depth + 1 if parent else 0,
        ) if original else None
        fields = dict(id=key, owner_id=owner.id, text="A post", created_at=now, updated_at=now, reply=reply)
        value = MicroPost.model_construct(**(fields | changes))
        posts[key] = value
        return value

    def article(owner, **changes):
        """Create a published article for reply-context scenarios.

        :param owner: Account owning the article.
        :param changes: Field overrides for private states.
        :return: The stored article document.
        """
        fields = dict(id=PydanticObjectId(), owner_id=owner.id, title="Article", summary="Preview",
                      body={"type": "doc", "content": []}, status="published", published_at=now,
                      created_at=now, updated_at=now)
        value = Article.model_construct(**(fields | changes))
        articles[value.id] = value
        return value

    async def get_post(key, **kwargs):
        """Resolve a stored post.

        :param key: Post identifier.
        :param kwargs: Unused Beanie session options.
        :return: Matching document or None.
        """
        return posts.get(key)

    async def get_article(key, **kwargs):
        """Resolve a stored article.

        :param key: Article identifier.
        :param kwargs: Unused Beanie session options.
        :return: Matching document or None.
        """
        return articles.get(key)

    async def users_by_ids(ids):
        """Resolve public author accounts in one simulated batch.

        :param ids: Requested account identifiers.
        :return: Existing matching accounts.
        """
        return [users[key] for key in ids if key in users]

    monkeypatch.setattr(MicroPost, "get", get_post)
    monkeypatch.setattr(Article, "get", get_article)
    monkeypatch.setattr(ProfileRepository, "users_by_ids", users_by_ids)
    return SimpleNamespace(posts=posts, articles=articles, users=users, user=user, post=post, article=article, now=now)


@pytest.fixture
def thread_store(publication_store, monkeypatch):
    """Replace only Beanie's aggregate I/O while retaining thread selection and presentation.

    :param publication_store: Isolated canonical documents.
    :param monkeypatch: Pytest restoration of persistence boundaries.
    :return: Publication store whose aggregation records all requested batches.
    """
    calls = []

    class Rows:
        """Minimal asynchronous Beanie result boundary for candidate documents."""

        def __init__(self, rows):
            """Retain candidate rows.

            :param rows: Documents returned by the simulated database.
            :return: None.
            """
            self.rows = rows

        async def to_list(self):
            """Serialize canonical documents as database rows.

            :return: Stored rows, leaving graph eligibility to the production selector.
            """
            return [post.model_dump(by_alias=True) for post in self.rows]

    def aggregate(pipeline, **kwargs):
        """Select candidate rows from the aggregate's initial indexed filter.

        :param pipeline: Actual production aggregation pipeline.
        :param kwargs: Unused Beanie query options.
        :return: Asynchronous candidate result.
        """
        calls.append(pipeline)
        match = pipeline[0]["$match"]
        roots = match["reply.publication_id"]["$in"]
        owners = match["owner_id"]["$in"]
        return Rows([post for post in publication_store.posts.values() if post.reply is not None
                     and post.reply.publication_id in roots and post.owner_id in owners])

    monkeypatch.setattr(MicroPost, "aggregate", aggregate)
    def collection():
        """Permit document validation without an initialized database connection.

        :return: None.
        """
        return None

    monkeypatch.setattr(MicroPost, "get_pymongo_collection", staticmethod(collection))
    publication_store.aggregate_calls = calls
    return publication_store
