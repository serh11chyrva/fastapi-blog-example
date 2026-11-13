"""Pure articles response mapping with already loaded authors."""

from backend.articles.models import Article
from backend.articles.schemas import ArticleResponse
from backend.articles.urls import article_thumbnail_url
from backend.profiles.models import User
from backend.profiles.presenters import user_card
from backend.publications.attachments import display_attachments
from backend.publications.urls import share_path
from backend.storage.urls import publication_image_url


def article_response(article: Article, authors: list[User]) -> ArticleResponse:
    """Present an article using its already loaded authors in stored order.

    :param article: Article document to present.
    :param authors: All author accounts in stored order, with the owner first.
    :return: The article response including body and publication metadata.
    """
    return ArticleResponse(
        id=str(article.id),
        owner_id=str(article.owner_id),
        attachments=display_attachments(
            article.attachments, [publication_image_url(key, "article-images") for key in article.inline_image_keys]
        ),
        share_url=share_path(authors[0].username, article.title, article.share_id),
        title=article.title,
        hero_layout=article.hero_layout,
        comments_enabled=article.comments_enabled,
        search_enabled=article.search_enabled,
        summary=article.summary,
        body=article.body,
        thumbnail_url=article_thumbnail_url(article.thumbnail_key),
        inline_image_urls=[publication_image_url(key, "article-images") for key in article.inline_image_keys],
        status=article.status,
        read_only=article.archived_at is not None or article.status != "published",
        archived_at=article.archived_at,
        pinned_at=article.pinned_at,
        authors=[user_card(author) for author in authors],
        created_at=article.created_at,
        updated_at=article.updated_at,
        scheduled_at=article.scheduled_at,
        published_at=article.published_at,
    )
