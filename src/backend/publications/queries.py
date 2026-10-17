"""Resolve public share links across independent publication features."""

import re

from backend.articles.models import Article
from backend.articles.repository import ArticleRepository
from backend.core.errors import NotFound
from backend.posts.models import MicroPost
from backend.posts.repository import PostRepository
from backend.profiles.models import User


async def shared(username: str, slug: str) -> tuple[MicroPost | Article, User]:
    """Resolve a stable share ID for an author's public publication.

    :param username: Public profile handle, optionally prefixed with @.
    :param slug: Readable share slug ending with the stable publication share ID.
    :return: The visible publication and its author.
    """
    share_id = slug.rsplit("--", 1)[-1]

    if not re.fullmatch(r"[0-9a-f]{32}", share_id):
        raise NotFound("Publication not found")

    author = await User.find_one(User.username == username.lower().removeprefix("@"))

    if author is None:
        raise NotFound("Publication not found")

    post = await PostRepository.find_shared(author.id, share_id)

    if post is not None:
        return post, author

    article = await ArticleRepository.find_shared(author.id, share_id)

    if article is None:
        raise NotFound("Publication not found")

    return article, author
