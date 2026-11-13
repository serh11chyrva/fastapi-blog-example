"""Shared visibility rules for public interactions and owner-only archive reads."""

from typing import Literal

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.articles.models import Article
from backend.core.errors import Forbidden, NotFound
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


async def readable_publication_path(
    kind: PublicationKind,
    publication_id: str,
    viewer_id: PydanticObjectId | None = None,
    session: AsyncClientSession | None = None,
    *,
    touch: bool = False,
    allow_deleted_reply: bool = False,
    discussion_write: bool = False,
) -> list[MicroPost | Article]:
    """Read authorized dependencies in selected, original, then nearest-parent order.

    Deleted reply ancestors retain navigation to surviving children. Each archive
    grants read access only to its owner. Visibility dependencies are touched for
    mutations so archiving or disabling comments conflicts with concurrent interactions.
    Disabled article discussions are hidden even from archive owners.

    :param kind: Publication collection to read.
    :param publication_id: String publication identifier.
    :param viewer_id: Optional account allowed to read its own archived content.
    :param session: Optional caller transaction session.
    :param touch: Increment internal revisions to serialize visibility-sensitive writes.
    :param allow_deleted_reply: Permit a selected deleted reply only for content-free navigation.
    :param discussion_write: Also check direct article discussions and return 403 when comments are disabled.
    :return: Authorized dependency documents; inaccessible resources raise not-found.
    """
    model = MicroPost if kind == "micro_post" else Article
    publication = await model.get(object_id(publication_id), session=session)
    if publication is None or (publication.deleted_at is not None and not (
        allow_deleted_reply and isinstance(publication, MicroPost) and publication.reply is not None
    )):
        raise NotFound("Publication not found")
    dependencies: list[MicroPost | Article] = [publication]
    if isinstance(publication, MicroPost) and publication.reply is not None:
        context = publication.reply
        original_model = MicroPost if context.kind == "micro_post" else Article
        original = await original_model.get(context.publication_id, session=session)
        if (original is None or original.deleted_at is not None
                or isinstance(original, MicroPost) and original.reply is not None):
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
        if isinstance(item, Article) and not item.comments_enabled and (discussion_write or item is not publication):
            if discussion_write:
                raise Forbidden("Comments are disabled for this article")
            raise NotFound("Publication not found")
        if touch:
            if session is None:
                raise ValueError("Publication mutation guards require a transaction")
            await item.update({"$inc": {"interaction_revision": 1}}, session=session)
    return dependencies


async def writable_discussion(
    kind: PublicationKind, publication_id: str, session: AsyncClientSession,
) -> MicroPost | Article:
    """Guard a new comment against disabled discussions and all original visibility dependencies.

    :param kind: Collection containing the article, original post, or selected reply.
    :param publication_id: Public target identifier for the new comment.
    :param session: Caller transaction whose guard writes serialize discussion changes.
    :return: The public target; disabled article discussions raise 403 at any reply depth.
    """
    path = await readable_publication_path(
        kind, publication_id, session=session, touch=True, discussion_write=True,
    )
    return path[0]


async def readable_discussion(
    kind: PublicationKind, publication_id: str, viewer_id: PydanticObjectId | None = None,
) -> MicroPost | Article:
    """Require a visible discussion without hiding the containing article itself.

    :param kind: Collection containing the article, original post, or selected reply.
    :param publication_id: Identifier whose discussion is requested.
    :param viewer_id: Optional owner allowed to read an otherwise eligible archived discussion.
    :return: The readable target; disabled article discussions raise not-found for every viewer.
    """
    publication = await readable_publication(kind, publication_id, viewer_id)
    if isinstance(publication, Article) and not publication.comments_enabled:
        raise NotFound("Discussion not found")
    return publication


async def check_reply_discussion(
    publication: MicroPost, session: AsyncClientSession | None = None, *, touch: bool = False,
) -> None:
    """Apply discussion closure to owner-only paths that otherwise permit independent archive access.

    Other archive visibility behavior is preserved. Live reads still require the full
    publication path; this guard only denies replies whose existing original article
    disables comments. No exception is granted to the article or comment owner.

    :param publication: Post being read or changed through an owner-only path.
    :param session: Optional caller transaction for the original lookup and guard write.
    :param touch: Serialize a mutation against changes to the original article's settings.
    :return: None; a disabled original discussion raises not-found.
    """
    if publication.reply is None or publication.reply.kind != "article":
        return
    article = await Article.get(publication.reply.publication_id, session=session)
    if article is None:
        return
    if not article.comments_enabled:
        raise NotFound("Publication not found")
    if touch:
        if session is None:
            raise ValueError("Discussion mutation guards require a transaction")
        await article.update({"$inc": {"interaction_revision": 1}}, session=session)


async def readable_publication(
    kind: PublicationKind,
    publication_id: str,
    viewer_id: PydanticObjectId | None = None,
    session: AsyncClientSession | None = None,
    *,
    touch: bool = False,
) -> MicroPost | Article:
    """Require a live publication and authorized access to its entire discussion path.

    :param kind: Publication collection to read.
    :param publication_id: String publication identifier.
    :param viewer_id: Optional owner allowed to read its archived content.
    :param session: Optional caller transaction session.
    :param touch: Guard mutations against concurrent changes to visibility dependencies.
    :return: The accessible live publication; inaccessible resources raise not-found.
    """
    path = await readable_publication_path(kind, publication_id, viewer_id, session, touch=touch)
    return path[0]


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
