from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, JsonValue
from pymongo import ASCENDING, IndexModel

ImagePurpose = Literal["avatars", "profile-banners", "post-images", "article-covers", "article-images"]


class UploadFileRecord(BaseModel):
    """Immutable file metadata and temporary key for a prepared upload."""

    filename: str
    content_type: str
    size_bytes: int
    temporary_key: str


class ImageUpload(Document):
    """Upload session tracking immutable targets, confirmation leases, and results."""

    owner_id: PydanticObjectId
    target_id: PydanticObjectId
    purpose: ImagePurpose
    bucket: str
    files: list[UploadFileRecord]
    created_at: datetime
    expires_at: datetime
    status: Literal["pending", "processing", "completed"] = "pending"
    lease_token: str | None = None
    lease_until: datetime | None = None
    result: dict[str, JsonValue] | None = None

    class Settings:
        """Beanie collection and index configuration for ImageUpload."""

        name = "image_uploads"
        indexes = [
            IndexModel(
                [("expires_at", ASCENDING)],
                expireAfterSeconds=7 * 86400,
                name="uploads_retention",
            )
        ]


class ObjectCleanup(Document):
    """Persistent deletion job for a temporary, replaced, or abandoned image object."""

    bucket: str
    key: str
    not_before: datetime

    class Settings:
        """Beanie collection and index configuration for ObjectCleanup."""

        name = "object_cleanup"
        indexes = [IndexModel([("not_before", ASCENDING)], name="cleanup_due")]
