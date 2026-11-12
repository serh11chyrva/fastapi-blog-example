"""Shared visibility rules for public interactions and owner-only archive reads."""

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


async def readable_publication(
    kind: PublicationKind,
    publication_id: str,
    viewer_id: PydanticObjectId | None = None,
    session: AsyncClientSession | None = None,
    *,
    touch: bool = False,
) -> MicroPost | Article:
    """Require access to a publication, its original, and every archived ancestor.

    Deleted reply ancestors retain navigation to surviving children. Each archive
    grants read access only to its owner. Visibility dependencies are touched for
    mutations so archiving conflicts with concurrent interactions.

    :param kind: Publication collection to read.
    :param publication_id: String publication identifier.
    :param viewer_id: Optional account allowed to read its own archived content.
    :param session: Optional caller transaction session.
    :param touch: Increment internal revisions to serialize visibility-sensitive writes.
    :return: The accessible publication; inaccessible resources raise not-found.
    """
    model = MicroPost if kind == "micro_post" else Article
    publication = await model.get(object_id(publication_id), session=session)
    if publication is None or publication.deleted_at is not None:
        raise NotFound("Publication not found")
    dependencies: list[MicroPost | Article] = [publication]
    if isinstance(publication, MicroPost) and publication.reply is not None:
        context = publication.reply
        original_model = MicroPost if context.kind == "micro_post" else Article
        original = await original_model.get(context.publication_id, session=session)
        if original is None or original.deleted_at is not None:
            raise NotFound("Publication not found")
        dependencies.append(original)
        parent_id = context.parent_id
        visited = {publication.id}
        while parent_id is not None:
            if parent_id in visited:
                raise NotFound("Publication not found")
            visited.add(parent_id)
            parent = await MicroPost.get(parent_id, session=session)
            if (parent is None or parent.reply is None
                    or parent.reply.kind != context.kind
                    or parent.reply.publication_id != context.publication_id):
                raise NotFound("Publication not found")
            dependencies.append(parent)
            parent_id = parent.reply.parent_id

    for item in dependencies:
        if item.archived_at is not None and item.owner_id != viewer_id:
            raise NotFound("Publication not found")
        if isinstance(item, MicroPost) and item.pending:
            raise NotFound("Publication not found")
        if isinstance(item, Article) and item.status != "published":
            raise NotFound("Publication not found")
        if touch:
            if session is None:
                raise ValueError("Publication mutation guards require a transaction")
            await item.update({"$inc": {"interaction_revision": 1}}, session=session)
    return publication


async def public_publication(
    kind: PublicationKind,
    publication_id: str,
    session: AsyncClientSession | None = None,
    *,
    touch: bool = False,
) -> MicroPost | Article:
    """Require strictly public content and all discussion visibility dependencies.

    :param kind: Publication collection to read.
    :param publication_id: String publication identifier.
    :param session: Optional caller transaction session.
    :param touch: Guard writes against concurrent archival, deletion, or unpublishing.
    :return: The public publication; even an owner's archive is unavailable here.
    """
    return await readable_publication(kind, publication_id, session=session, touch=touch)


async def publication_is_public(kind: PublicationKind, publication_id: str) -> bool:
    """Determine whether interaction controls may be enabled for an authorized read.

    :param kind: Collection containing the already readable publication.
    :param publication_id: Publication identifier.
    :return: Whether the publication and its entire discussion context are public.
    """
    try:
        await public_publication(kind, publication_id)
    except NotFound:
        return False
    return True
