from backend.core.transactions import transaction
from loguru import logger
from backend.core.resources import AppResources
import asyncio
from datetime import UTC, datetime, timedelta
from typing import cast
from pydantic import JsonValue
from uuid import uuid4

from beanie import PydanticObjectId
from botocore.exceptions import BotoCoreError, ClientError
from backend.core.errors import Conflict, InvalidOperation, NotFound, Unavailable
from backend.audit.context import AuditContext
from backend.storage.attachments import ImageAttachments, UploadResult, saved_result
from backend.content.cache import invalidate_public_feed
from pymongo.errors import PyMongoError

from backend.content.models import Article
from backend.core.config import get_settings
from backend.core.errors import ApplicationError
from backend.storage.errors import ImageTooLarge, UnsupportedImage
from backend.profiles.models import User
from backend.storage.cleanup import queue_deletion
from backend.storage.models import ImagePurpose, ImageUpload, ObjectCleanup, UploadFileRecord
from backend.storage.s3 import image_type
from backend.storage.schemas import ImageUploadRequest, ImageUploadResponse, PresignedImageFile


EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


class ImageStorageService:
    def __init__(self, resources: AppResources, audit: AuditContext) -> None:
        self.resources = resources
        self.audit = audit
        self.attachments = ImageAttachments()

    def max_size(self, purpose: ImagePurpose) -> int:
        settings = get_settings()
        if purpose == "avatars":
            return settings.avatar_max_bytes
        return settings.article_thumbnail_max_bytes if purpose == "article-covers" else settings.publication_image_max_bytes

    async def create(self, owner: User, purpose: ImagePurpose, target_id: str, payload: ImageUploadRequest) -> ImageUploadResponse:
        try:
            return await self._create(owner, purpose, target_id, payload)
        except ApplicationError:
            raise
        except (BotoCoreError, PyMongoError) as exc:
            logger.exception("Failed to prepare image upload")
            raise Unavailable("Image storage or database is unavailable") from exc

    async def _create(self, owner: User, purpose: ImagePurpose, target_id: str, payload: ImageUploadRequest) -> ImageUploadResponse:
        target = await self.attachments.target(purpose, target_id, owner)
        if purpose != "post-images" and len(payload.files) != 1:
            raise InvalidOperation("Choose exactly one image")
        if purpose == "article-images" and isinstance(target, Article) and len(target.inline_image_keys) >= 30:
            raise InvalidOperation("An article can contain up to 30 inline images")
        limit = self.max_size(purpose)
        if any(file.size_bytes > limit for file in payload.files):
            raise ImageTooLarge("Image exceeds the configured size limit")
        settings = get_settings()
        now = datetime.now(UTC)
        upload = ImageUpload(
            owner_id=owner.id, target_id=target.id, purpose=purpose,
            bucket=settings.avatar_bucket if purpose == "avatars" else settings.publication_bucket,
            created_at=now, expires_at=now + timedelta(seconds=settings.upload_expiry_seconds),
            files=[UploadFileRecord(**file.model_dump(), temporary_key=f"temporary/{uuid4().hex}") for file in payload.files],
        )
        instructions = []
        for file in upload.files:
            url = await asyncio.to_thread(
                self.resources.s3_public.generate_presigned_url, "put_object",
                Params={"Bucket": upload.bucket, "Key": file.temporary_key, "ContentType": file.content_type},
                ExpiresIn=settings.upload_expiry_seconds, HttpMethod="PUT",
            )
            instructions.append(PresignedImageFile(upload_url=url, headers={"Content-Type": file.content_type}, max_size_bytes=limit))
        async with transaction(self.resources.mongo) as db_session:
            await upload.insert(session=db_session)
            for file in upload.files:
                await queue_deletion(upload.bucket, file.temporary_key, not_before=upload.expires_at + timedelta(hours=1), session=db_session)
        return ImageUploadResponse(upload_id=str(upload.id), expires_at=upload.expires_at, files=instructions)

    async def _copy_and_validate(self, upload: ImageUpload, keys: list[str]) -> None:
        client = self.resources.s3
        for file, key in zip(upload.files, keys, strict=True):
            try:
                await asyncio.to_thread(
                    client.copy_object, Bucket=upload.bucket, Key=key,
                    CopySource={"Bucket": upload.bucket, "Key": file.temporary_key},
                    MetadataDirective="REPLACE", ContentType=file.content_type,
                )
            except ClientError as exc:
                if exc.response["Error"]["Code"] in {"NoSuchKey", "404", "NotFound"}:
                    raise Conflict("Upload all files before confirming") from exc
                raise
            info = await asyncio.to_thread(client.head_object, Bucket=upload.bucket, Key=key)
            if info["ContentLength"] > self.max_size(upload.purpose):
                raise ImageTooLarge("Image exceeds the configured size limit")
            if info["ContentLength"] != file.size_bytes:
                raise InvalidOperation("Uploaded size does not match the requested size")
            result = await asyncio.to_thread(client.get_object, Bucket=upload.bucket, Key=key, Range="bytes=0-11")
            body = result["Body"]
            try:
                signature = await asyncio.to_thread(body.read, 12)
            finally:
                body.close()
            if image_type(signature) != (file.content_type, EXTENSIONS[file.content_type]):
                raise UnsupportedImage("Use JPEG, PNG, or WebP bytes matching the requested content type")

    async def complete(self, owner: User, purpose: ImagePurpose, target_id: str, upload_id: str) -> UploadResult:
        """Confirm an owned upload once and replay its validated saved result.

        A five-minute lease serializes confirmation. S3 copying and validation run
        before the MongoDB transaction. Attachment, audit, result, and cleanup
        changes commit together; failed or uncertain copies retain cleanup jobs.
        Avatar HTTP responses separately load current owner settings on replay.
        """
        try:
            return await self._complete(owner, purpose, target_id, upload_id)
        except ApplicationError:
            raise
        except (BotoCoreError, PyMongoError) as exc:
            logger.exception("Failed to confirm image upload")
            raise Unavailable("Image storage or database is unavailable; retry confirmation") from exc

    async def _complete(self, owner: User, purpose: ImagePurpose, target_id: str, upload_id: str) -> UploadResult:
        await self.attachments.target(purpose, target_id, owner)
        if not PydanticObjectId.is_valid(upload_id):
            raise NotFound("Upload not found")
        upload = await ImageUpload.get(PydanticObjectId(upload_id))
        if upload is None or upload.owner_id != owner.id or upload.purpose != purpose or upload.target_id != PydanticObjectId(target_id):
            raise NotFound("Upload not found")
        if upload.status == "completed":
            return saved_result(upload)
        now = datetime.now(UTC)
        if upload.expires_at <= now:
            raise Conflict("Upload has expired; request new upload URLs")
        token = uuid4().hex
        claim = await ImageUpload.find_one({
            "_id": upload.id, "expires_at": {"$gt": now},
            "$or": [{"status": "pending"}, {"status": "processing", "lease_until": {"$lte": now}}],
        }).update({"$set": {"status": "processing", "lease_token": token, "lease_until": now + timedelta(minutes=5)}})
        if claim.modified_count != 1:
            current = await ImageUpload.get(upload.id)
            if current is not None and current.status == "completed":
                return saved_result(current)
            raise Conflict("Upload confirmation is already in progress")
        keys = [f"{purpose}/{uuid4().hex}.{EXTENSIONS[file.content_type]}" for file in upload.files]
        try:
            for key in keys:
                await queue_deletion(upload.bucket, key, not_before=now + timedelta(hours=1))
            await self._copy_and_validate(upload, keys)
            result = await self._attach(owner, upload, keys, token)
        except Exception as exc:
            await ImageUpload.find_one({"_id": upload.id, "status": "processing", "lease_token": token}).update(
                {"$set": {"status": "pending", "lease_token": None, "lease_until": None}}
            )
            # Keep cleanup records until a committed attachment can be ruled out.
            if isinstance(exc, ApplicationError):
                await ObjectCleanup.find({"bucket": upload.bucket, "key": {"$in": keys}}).update(
                    {"$set": {"not_before": datetime.now(UTC)}}
                )
                raise
            raise
        await invalidate_public_feed(self.resources.redis)
        return result

    async def _attach(self, owner: User, upload: ImageUpload, keys: list[str], token: str) -> UploadResult:
        """Commit a result only while this confirmation still owns its lease."""
        async with transaction(self.resources.mongo) as db_session:
            current = await ImageUpload.get(upload.id, session=db_session)
            if current is None or current.status != "processing" or current.lease_token != token or current.lease_until is None or current.lease_until <= datetime.now(UTC):
                raise Conflict("Confirmation lease expired; retry confirmation")
            attachment = await self.attachments.apply(upload, keys, owner, self.audit, db_session)
            result = attachment.response
            current.status = "completed"
            current.result = cast(dict[str, JsonValue], result.model_dump(mode="json"))
            current.lease_token = None
            current.lease_until = None
            await current.save(session=db_session)
            await ObjectCleanup.find({"bucket": upload.bucket, "key": {"$in": keys}}).delete(session=db_session)
            for key in attachment.replaced_keys:
                await queue_deletion(upload.bucket, key, session=db_session)
        return result
