"""Resolve public share links across independent publication features."""

import re

from beanie import PydanticObjectId

from backend.articles.models import Article
from backend.articles.repository import ArticleRepository
from backend.core.errors import NotFound
from backend.posts.models import MicroPost
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


async def shared(username: str, slug: str) -> tuple[MicroPost | Article, list[User]]:
    """Resolve a stable share ID for an owner's public publication.

    :param username: Public profile handle, optionally prefixed with @.
    :param slug: Readable share slug ending with the stable publication share ID.
    :return: The visible publication and all its authors in stored order.
    """
    share_id = slug.rsplit("--", 1)[-1]

    if not re.fullmatch(r"[0-9a-f]{32}", share_id):
        raise NotFound("Publication not found")

    owner = await ProfileRepository.find_by_username(username)

    if owner is None:
        raise NotFound("Publication not found")

    post = await PostRepository.find_shared(owner.id, share_id)

    if post is not None:
        return post, await load_authors(post.author_ids)

    article = await ArticleRepository.find_shared(owner.id, share_id)

    if article is None:
        raise NotFound("Publication not found")

    return article, await load_authors(article.author_ids)
