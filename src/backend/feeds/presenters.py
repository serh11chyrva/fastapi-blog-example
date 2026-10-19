"""Map publications to the mixed feed contract."""

from backend.articles.models import Article
from backend.articles.urls import article_thumbnail_url
from backend.feeds.schemas import ArticleFeedItem, FeedItem, PostFeedItem
from backend.posts.models import MicroPost
from backend.profiles.models import User
from backend.profiles.presenters import user_card
from backend.publications.attachments import display_attachments
from backend.publications.urls import share_path
from backend.storage.urls import publication_image_url


def feed_item(publication: MicroPost | Article, authors: list[User]) -> FeedItem:
    """Present a publication as the corresponding feed item type.

    :param publication: Micro-post or article document to present.
    :param authors: All author accounts in stored order, with the owner first.
    :return: The micro-post or article feed item.
    """
    if isinstance(publication, MicroPost):
        image_urls = [publication_image_url(key, "post-images") for key in publication.image_keys]
    else:
        image_urls = [publication_image_url(key, "article-images") for key in publication.inline_image_keys]

    common = dict(
        id=str(publication.id),
        owner_id=str(publication.owner_id),
        authors=[user_card(author) for author in authors],
        attachments=display_attachments(publication.attachments, image_urls),
    )

    if isinstance(publication, MicroPost):
        return PostFeedItem(
            **common,
            share_url=share_path(authors[0].username, publication.text, publication.share_id),
            text=publication.text,
            published_at=publication.created_at,
        )

    if publication.published_at is None:
        raise ValueError("A feed article must have a publication timestamp")

    return ArticleFeedItem(
        **common,
        share_url=share_path(authors[0].username, publication.title, publication.share_id),
        title=publication.title,
        summary=publication.summary,
        thumbnail_url=article_thumbnail_url(publication.thumbnail_key),
        published_at=publication.published_at,
    )
