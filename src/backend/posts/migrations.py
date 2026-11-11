from backend.posts.models import MicroPost
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from backend.posts.content import validate_post_content
from backend.publications.attachments import ImageAttachment, PublicationAttachment


class LegacyPostOwner(BaseModel):
    """Project legacy author identities without parsing the modern ownership contract."""

    id: PydanticObjectId = Field(alias="_id")
    author_id: PydanticObjectId


async def backfill_legacy_post_owners() -> None:
    """Copy authoritative legacy author IDs into missing post ownership fields.

    Keep the legacy field, timestamps, and existing owners untouched. Projection
    permits reading records that cannot yet validate as modern MicroPost documents.

    :return: None; unsupported records without a legacy author fail without guessing ownership.
    """
    async for legacy in MicroPost.find({"owner_id": {"$exists": False}}).project(LegacyPostOwner):
        await MicroPost.find_one({"_id": legacy.id, "owner_id": {"$exists": False}}).update(
            {"$set": {"owner_id": legacy.author_id}},
        )


class AttachmentBackup(Document):
    """Preserve legacy descriptors and per-post normalization checkpoints."""

    id: PydanticObjectId
    attachments: list[PublicationAttachment] = Field(default_factory=list)
    complete: bool = False

    class Settings:
        """Store retained legacy attachment data separately from live posts."""

        name = "post_attachment_backups"


async def normalize_attachments() -> int:
    """Backfill legacy ownership and keep one attachment choice without changing timestamps.

    :return: Number of newly normalized posts; completed checkpoints are not rewritten.
    """
    await backfill_legacy_post_owners()
    changed = 0
    async for post in MicroPost.find({"pending": {"$ne": True}}):
        backup = await AttachmentBackup.get(post.id)
        if backup is not None and backup.complete:
            continue
        if backup is None:
            backup = AttachmentBackup(id=post.id, attachments=post.attachments)
            await backup.insert()
        if post.image_keys:
            post.attachments = [item for item in post.attachments if isinstance(item, ImageAttachment)][:5]
        else:
            post.attachments = [item for item in post.attachments
                                if item.type in {"og_card", "embed", "article", "post", "link"}][:1]
        if post.deleted_at is None:
            validate_post_content(post.text, post.attachments, post.image_keys)
        await post.save()
        backup.complete = True
        await backup.save()
        changed += 1
    return changed


async def ensure_public_share_ids() -> None:
    """Backfill stable share keys for existing posts without replacing persisted identities.

    :return: None.
    """
    for item in await MicroPost.find({"share_id": {"$exists": False}}).to_list():
        item.share_id = f"10000000{item.id}"
        await item.save()
