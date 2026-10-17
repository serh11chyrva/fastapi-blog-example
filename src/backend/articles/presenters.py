"""Pure articles response mapping with an already loaded author."""

from backend.articles.models import Article
from backend.articles.schemas import ArticleResponse
from backend.articles.urls import article_thumbnail_url
from backend.profiles.models import User
from backend.profiles.presenters import avatar_url
from backend.publications.urls import share_path
from backend.storage.urls import publication_image_url


def article_response(article: Article, author: User) -> ArticleResponse:
    """Present an article using its already loaded author.

    :param article: Article document to present.
    :param author: Already loaded account that authored the publication.
    :return: The article response including body and publication metadata.
    """
    return ArticleResponse(
        id=str(article.id),
        share_url=share_path(author.username, article.title, article.share_id),
        title=article.title,
        summary=article.summary,
        body=article.body,
        thumbnail_url=article_thumbnail_url(article.thumbnail_key),
        inline_image_urls=[publication_image_url(key, "article-images") for key in article.inline_image_keys],
        status=article.status,
        author_id=str(author.id),
        author_username=author.username,
        author_display_name=author.display_name,
        author_avatar_url=avatar_url(author),
        created_at=article.created_at,
        updated_at=article.updated_at,
        scheduled_at=article.scheduled_at,
        published_at=article.published_at,
    )
