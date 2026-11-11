"""Shared public-publication access rules for interactions and discussions."""

from typing import Literal

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.articles.models import Article
from backend.core.errors import NotFound
from backend.posts.models import MicroPost

type PublicationKind = Literal["micro_post", "article"]


def object_id(value: str) -> PydanticObjectId:
    """Parse a resource ID without exposing malformed or missing resources.

    :param value: Resource identifier supplied by the caller.
    :return: The validated ObjectId; malformed input raises a not-found error.
    """
    if not PydanticObjectId.is_valid(value):
        raise NotFound("Resource not found")

    return PydanticObjectId(value)


async def public_publication(
    kind: PublicationKind,
    publication_id: str,
    session: AsyncClientSession | None = None,
    *,
    touch: bool = False,
) -> MicroPost | Article:
    """Require a public publication, optionally serializing mutations against visibility changes.

    :param kind: Publication collection to read.
    :param publication_id: String identifier of the containing publication.
    :param session: Optional session for the caller's transaction.
    :param touch: Increment an internal revision in the transaction to conflict with deletion or unpublishing.
    :return: An undeleted post or published article; even an owner's draft is unavailable here.
    """
    model = MicroPost if kind == "micro_post" else Article
    publication = await model.get(object_id(publication_id), session=session)

    if publication is None or publication.deleted_at is not None:
        raise NotFound("Publication not found")

    if isinstance(publication, MicroPost) and publication.pending:
        raise NotFound("Publication not found")

    if isinstance(publication, Article) and publication.status != "published":
        raise NotFound("Publication not found")

    if isinstance(publication, MicroPost) and publication.reply is not None:
        context = publication.reply
        await public_publication(context.kind, str(context.publication_id), session, touch=touch)

    if touch:
        if session is None:
            raise ValueError("Publication mutation guards require a transaction")

        await publication.update({"$inc": {"interaction_revision": 1}}, session=session)

    return publication
