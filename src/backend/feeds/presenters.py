"""Map publications to the mixed feed contract."""

from backend.articles.models import Article
from backend.articles.urls import article_thumbnail_url
from backend.feeds.schemas import ArticleFeedItem, FeedItem, PostFeedItem
from backend.posts.models import MicroPost
from backend.profiles.models import User
from backend.profiles.presenters import avatar_url
from backend.publications.urls import share_path
from backend.storage.urls import publication_image_url


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
