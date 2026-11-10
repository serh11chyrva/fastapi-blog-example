"""Map publications to the mixed feed contract."""

from typing import cast

from backend.articles.models import Article, ArticlePreviewSource
from backend.articles.urls import article_thumbnail_url
from backend.feeds.schemas import ArticleFeedItem, ArticlePreview, PostFeedItem, PostPreview, RepostFeedItem
from backend.interactions.models import PublicationInteraction
from backend.posts.models import MicroPost
from backend.profiles.models import User
from backend.profiles.presenters import user_card
from backend.publications.attachments import display_attachments
from backend.publications.urls import share_path
from backend.storage.urls import publication_image_url


def feed_item(publication: MicroPost | Article, authors: list[User]) -> PostFeedItem | ArticleFeedItem:
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
        updated_at=publication.updated_at,
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


def publication_preview(
    publication: MicroPost | Article | ArticlePreviewSource, authors: list[User],
) -> ArticlePreview | PostPreview:
    """Build a public card without nested content or viewer state.

    :param publication: Public post or published article.
    :param authors: Public author accounts in stored order.
    :return: The compact original card.
    """
    if isinstance(publication, MicroPost):
        return PostPreview(
            id=str(publication.id),
            share_url=share_path(authors[0].username, publication.text, publication.share_id),
            authors=[user_card(author) for author in authors],
            text=publication.text,
            thumbnail_url=(
                publication_image_url(publication.image_keys[0], "post-images") if publication.image_keys else None
            ),
            published_at=publication.created_at,
            updated_at=publication.updated_at,
        )

    if publication.published_at is None:
        raise ValueError("An article preview requires a publication timestamp")

    return ArticlePreview(
        id=str(publication.id),
        share_url=share_path(authors[0].username, publication.title, publication.share_id),
        authors=[user_card(author) for author in authors],
        title=publication.title,
        summary=publication.summary,
        thumbnail_url=article_thumbnail_url(publication.thumbnail_key),
        published_at=publication.published_at,
    )


def repost_item(
    post: MicroPost, authors: list[User], repost: PublicationInteraction, reposter: User,
) -> RepostFeedItem:
    """Wrap an original post without replacing its owner or featured-author attribution.

    :param post: Currently public original micro-post.
    :param authors: Original post authors in display order.
    :param repost: Public repost edge supplying event identity and timestamp.
    :param reposter: Account that reposted the original.
    :return: The repost event with a compact original-post representation.
    """
    return RepostFeedItem(
        id=str(repost.id), reposted_by=user_card(reposter), published_at=repost.created_at,
        post=cast(PostFeedItem, feed_item(post, authors)),
    )
