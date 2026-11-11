from backend.posts.models import MicroPost
from beanie import Document, PydanticObjectId
from pydantic import Field

from backend.posts.content import validate_post_content
from backend.publications.attachments import ImageAttachment, PublicationAttachment


class AttachmentBackup(Document):
    """Preserve legacy descriptors and per-post normalization checkpoints."""

    id: PydanticObjectId
    attachments: list[PublicationAttachment] = Field(default_factory=list)
    complete: bool = False

    class Settings:
        """Store retained legacy attachment data separately from live posts."""

        name = "post_attachment_backups"


async def normalize_attachments() -> int:
    """Keep a gallery or the first supported non-image choice without changing timestamps.

    :return: Number of newly normalized posts; completed checkpoints are not rewritten.
    """
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
