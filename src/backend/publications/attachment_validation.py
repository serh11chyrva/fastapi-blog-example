"""Validate publication attachment references within the caller's write transaction."""

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.articles.models import Article
from backend.core.errors import InvalidOperation
from backend.profiles.models import User
from backend.publications.attachments import (
    ArticleAttachment,
    ImageAttachment,
    MentionAttachment,
    PublicationAttachment,
    VideoAttachment,
)


async def validate_attachment_references(
    attachments: list[PublicationAttachment],
    image_urls: list[str],
    session: AsyncClientSession,
) -> None:
    """Reject foreign media, nonexistent mentions, private articles, and reserved video attachments.

    References are checked at write time. Later deletion or unpublishing does not copy or expose
    referenced data: readers must resolve IDs through the normal visibility-enforcing endpoints.

    :param attachments: Bounded, structurally validated attachment descriptors supplied by the caller.
    :param image_urls: Uploaded images already belonging to the containing publication; empty on creation.
    :param session: MongoDB session for the publication mutation and its audit event.
    :return: None.
    """
    mentions: set[PydanticObjectId] = set()
    articles: set[PydanticObjectId] = set()
    images: set[str] = set()

    for item in attachments:
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

    if mentions and await User.find({"_id": {"$in": list(mentions)}}, session=session).count() != len(mentions):
        raise InvalidOperation("Mentioned account does not exist")

    if articles:
        count = await Article.find(
            {"_id": {"$in": list(articles)}, "status": "published", "deleted_at": None}, session=session
        ).count()

        if count != len(articles):
            raise InvalidOperation("Article attachments must reference existing published articles")
