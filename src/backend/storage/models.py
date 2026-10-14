from datetime import datetime
from typing import Any, Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel
from pymongo import ASCENDING, IndexModel


ImagePurpose = Literal["avatars", "post-images", "article-covers", "article-images"]


class UploadFileRecord(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    temporary_key: str


class ImageUpload(Document):
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
    result: dict[str, Any] | None = None

    class Settings:
        name = "image_uploads"
        indexes = [IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=7 * 86400, name="uploads_retention")]


class ObjectCleanup(Document):
    bucket: str
    key: str
    not_before: datetime

    class Settings:
        name = "object_cleanup"
        indexes = [IndexModel([("not_before", ASCENDING)], name="cleanup_due")]
