"""Validate publication attachment references within the caller's write transaction."""

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.articles.models import Article
from backend.links.players import player_resource
from backend.core.errors import InvalidOperation
from backend.posts.models import MicroPost
from backend.profiles.models import User
from backend.publications.attachments import (
    ArticleAttachment,
    EmbedAttachment,
    ImageAttachment,
    MentionAttachment,
    PostAttachment,
    PublicationAttachment,
    VideoAttachment,
)


async def validate_attachment_references(
    attachments: list[PublicationAttachment],
    image_urls: list[str],
    session: AsyncClientSession,
    *,
    retained: list[PublicationAttachment] | None = None,
    post_id: PydanticObjectId | None = None,
) -> None:
    """Reject foreign media, nonexistent mentions, private articles, and reserved video attachments.

    References are checked at write time. Later deletion or unpublishing does not copy or expose
    referenced data: readers must resolve IDs through the normal visibility-enforcing endpoints.

    :param attachments: Bounded, structurally validated attachment descriptors supplied by the caller.
    :param image_urls: Uploaded images already belonging to the containing publication; empty on creation.
    :param session: MongoDB session for the publication mutation and its audit event.
    :param retained: Previously saved references allowed to remain after an original becomes private.
    :param post_id: Post being edited, when self-quotation must be rejected.
    :return: None.
    """
    mentions: set[PydanticObjectId] = set()
    articles: set[PydanticObjectId] = set()
    images: set[str] = set()
    posts: set[PydanticObjectId] = set()
    old_articles = {PydanticObjectId(item.article_id) for item in retained or [] if isinstance(item, ArticleAttachment)}
    old_posts = {PydanticObjectId(item.post_id) for item in retained or [] if isinstance(item, PostAttachment)}

    for item in attachments:
        if isinstance(item, EmbedAttachment):
            resource = player_resource(item.url)
            if resource is None or resource[0] != item.provider:
                if item not in (retained or []):
                    raise InvalidOperation("Use a concrete media resource or attach this URL as a link card")

        if isinstance(item, VideoAttachment):
            raise InvalidOperation("Video attachments are reserved and are not supported yet")

        if isinstance(item, ImageAttachment):
            if item.url not in image_urls:
                raise InvalidOperation("Attachment image must be uploaded to this publication")

            if item.url in images:
                raise InvalidOperation("An attachment image may only appear once")

            images.add(item.url)
        elif isinstance(item, MentionAttachment):
            mentions.add(PydanticObjectId(item.user_id))
        elif isinstance(item, ArticleAttachment):
            articles.add(PydanticObjectId(item.article_id))
        elif isinstance(item, PostAttachment):
            posts.add(PydanticObjectId(item.post_id))

    if mentions and await User.find({"_id": {"$in": list(mentions)}}, session=session).count() != len(mentions):
        raise InvalidOperation("Mentioned account does not exist")

    if post_id in posts:
        raise InvalidOperation("A post cannot quote itself")

    posts -= old_posts
    if posts and await MicroPost.find({"_id": {"$in": list(posts)}, "deleted_at": None}, session=session).count() != len(posts):
        raise InvalidOperation("Post attachments must reference existing public posts")

    articles -= old_articles
    if articles:
        count = await Article.find(
            {"_id": {"$in": list(articles)}, "status": "published", "deleted_at": None}, session=session
        ).count()

        if count != len(articles):
            raise InvalidOperation("Article attachments must reference existing published articles")
