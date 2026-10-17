"""Pure publication-to-response mapping with an explicitly supplied author."""

from backend.content.models import Article, MicroPost
from backend.content.schemas import (
    ArticleFeedItem,
    ArticleResponse,
    FeedItem,
    MicroPostResponse,
    PostFeedItem,
)
from backend.content.urls import (
    article_thumbnail_url,
    publication_image_url,
    share_path,
)
from backend.profiles.models import User
from backend.profiles.presenters import avatar_url


def post_response(post: MicroPost, author: User) -> MicroPostResponse:
    """Present a micro-post using its already loaded author.

    :param post: Micro-post document to present.
    :param author: Already loaded account that authored the publication.
    :return: The public micro-post response.
    """
    return MicroPostResponse(
        id=str(post.id),
        share_url=share_path(author.username, post.text, post.share_id),
        text=post.text,
        images=[publication_image_url(key, "post-images") for key in post.image_keys],
        author_id=str(author.id),
        author_username=author.username,
        author_display_name=author.display_name,
        author_avatar_url=avatar_url(author),
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


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


def feed_item(publication: MicroPost | Article, author: User) -> FeedItem:
    """Present a publication as the corresponding feed item type.

    :param publication: Micro-post or article document to present.
    :param author: Already loaded account that authored the publication.
    :return: The micro-post or article feed item.
    """
    common = dict(
        id=str(publication.id),
        author_id=str(author.id),
        author_username=author.username,
        author_display_name=author.display_name,
        author_avatar_url=avatar_url(author),
    )

    if isinstance(publication, MicroPost):
        return PostFeedItem(
            **common,
            share_url=share_path(author.username, publication.text, publication.share_id),
            text=publication.text,
            images=[publication_image_url(key, "post-images") for key in publication.image_keys],
            published_at=publication.created_at,
        )

    if publication.published_at is None:
        raise ValueError("A feed article must have a publication timestamp")

    return ArticleFeedItem(
        **common,
        share_url=share_path(author.username, publication.title, publication.share_id),
        title=publication.title,
        summary=publication.summary,
        thumbnail_url=article_thumbnail_url(publication.thumbnail_key),
        published_at=publication.published_at,
    )
