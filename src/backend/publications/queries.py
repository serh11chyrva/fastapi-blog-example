"""Resolve public share links across independent publication features."""

import re

from beanie import PydanticObjectId

from backend.articles.models import Article, ArticlePreviewSource
from backend.articles.repository import ArticleRepository
from backend.core.errors import InvalidOperation, NotFound
from backend.feeds.presenters import publication_preview
from backend.feeds.schemas import PublicationPreview
from backend.posts.models import MicroPost
from backend.posts.visibility import visible_post_stages
from backend.publications.access import readable_publication
from backend.posts.repository import PostRepository
from backend.profiles.models import User
from backend.profiles.repository import ProfileRepository


async def load_authors(author_ids: list[PydanticObjectId]) -> list[User]:
    """Load every publication author in stored order or reject missing accounts.

    :param author_ids: Owner identifier followed by featured author identifiers in display order.
    :return: Author accounts in the same order, with the owner first.
    """
    by_id = {user.id: user for user in await ProfileRepository.users_by_ids(author_ids)}

    if any(author_id not in by_id for author_id in author_ids):
        raise NotFound("Author not found")

    return [by_id[author_id] for author_id in author_ids]


async def publication_previews(refs: list[str]) -> list[PublicationPreview]:
    """Load bounded public references and their author cards in batches.

    :param refs: Ordered typed references in kind:id format.
    :return: Compact cards for visible originals, deduplicated in request order.
    """
    keys = {}
    for ref in refs:
        kind, _, value = ref.partition(":")
        if kind not in {"article", "micro_post"} or not re.fullmatch(r"[0-9a-fA-F]{24}", value):
            raise InvalidOperation("Use article:<id> or micro_post:<id> for publication references")

        keys[kind, PydanticObjectId(value)] = None

    article_ids = [value for kind, value in keys if kind == "article"]
    post_ids = [value for kind, value in keys if kind == "micro_post"]
    articles = await Article.find({
        "_id": {"$in": article_ids}, "deleted_at": None, "archived_at": None, "status": "published", "published_at": {"$ne": None},
    }).project(ArticlePreviewSource).to_list() if article_ids else []
    rows = await MicroPost.aggregate([
        {"$match": {"_id": {"$in": post_ids}, "deleted_at": None}}, *visible_post_stages(),
    ]).to_list() if post_ids else []
    posts = [MicroPost.model_validate(row) for row in rows]
    originals: dict[tuple[str, PydanticObjectId], ArticlePreviewSource | MicroPost] = {
        ("article", item.id): item for item in articles
    }
    originals.update({("micro_post", item.id): item for item in posts})
    authors = {user.id: user for user in await ProfileRepository.users_by_ids(
        list({author_id for original in originals.values() for author_id in original.author_ids})
    )}

    return [
        publication_preview(original, [authors[author_id] for author_id in original.author_ids])
        for key in keys
        if (original := originals.get(key)) is not None and all(author_id in authors for author_id in original.author_ids)
    ]


async def shared(username: str, slug: str, viewer_id: PydanticObjectId | None = None) -> tuple[MicroPost | Article, list[User]]:
    """Resolve a stable share ID with current public or owner-only archive visibility.

    :param username: Public profile handle, optionally prefixed with @.
    :param slug: Readable share slug ending with the stable publication share ID.
    :param viewer_id: Optional owner permitted to read archived content.
    :return: The accessible publication and its ordered author accounts.
    """
    share_id = slug.rsplit("--", 1)[-1]

    if not re.fullmatch(r"[0-9a-f]{32}", share_id):
        raise NotFound("Publication not found")

    owner = await ProfileRepository.find_by_username(username)

    if owner is None:
        raise NotFound("Publication not found")

    post = await PostRepository.find_shared(owner.id, share_id)

    if post is not None:
        if post.archived_at is None or post.owner_id != viewer_id:
            await readable_publication("micro_post", str(post.id), viewer_id)
        return post, await load_authors(post.author_ids)

    article = await ArticleRepository.find_shared(owner.id, share_id)

    if article is None:
        raise NotFound("Publication not found")

    await readable_publication("article", str(article.id), viewer_id)
    return article, await load_authors(article.author_ids)
