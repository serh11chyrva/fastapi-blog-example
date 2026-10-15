from backend.core.transactions import transaction
from loguru import logger
from backend.core.resources import get_resources
import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from beanie import PydanticObjectId
from botocore.exceptions import ClientError
from fastapi import HTTPException, Request
from pymongo.errors import OperationFailure

from backend.content.models import Article, MicroPost
from backend.content.service import ContentService
from backend.content.urls import publication_image_url
from backend.audit.service import record_audit
from backend.audit.dependencies import audit_context
from backend.core.config import get_settings
from backend.core.errors import ApplicationError
from backend.profiles.models import User
from backend.profiles.service import ProfileService
from backend.storage.cleanup import queue_deletion
from backend.storage.models import ImagePurpose, ImageUpload, ObjectCleanup, UploadFileRecord
from backend.storage.s3 import image_type
from backend.storage.schemas import ImageUploadRequest, ImageUploadResponse, PresignedImageFile


EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


class ImageStorageService:
    async def target(self, purpose: ImagePurpose, target_id: str, owner: User, *, session: Any = None) -> User | MicroPost | Article:
        if not PydanticObjectId.is_valid(target_id):
            raise HTTPException(404, "Resource not found")
        model = User if purpose == "avatars" else MicroPost if purpose == "post-images" else Article
        target = await model.get(PydanticObjectId(target_id), session=session)
        if target is None or (purpose == "avatars" and target.id != owner.id) or (
            purpose != "avatars" and (target.deleted_at is not None or target.author_id != owner.id)
        ):
            raise HTTPException(404, "Resource not found")
        return target

    def max_size(self, purpose: ImagePurpose) -> int:
        settings = get_settings()
        if purpose == "avatars":
            return settings.avatar_max_bytes
        return settings.article_thumbnail_max_bytes if purpose == "article-covers" else settings.publication_image_max_bytes

    async def create(self, request: Request, owner: User, purpose: ImagePurpose, target_id: str, payload: ImageUploadRequest) -> ImageUploadResponse:
        try:
            return await self._create(request, owner, purpose, target_id, payload)
        except (HTTPException, ApplicationError):
            raise
        except Exception as exc:
            logger.exception("Failed to prepare image upload")
            raise HTTPException(503, "Image storage or database is unavailable") from exc

    async def _create(self, request: Request, owner: User, purpose: ImagePurpose, target_id: str, payload: ImageUploadRequest) -> ImageUploadResponse:
        target = await self.target(purpose, target_id, owner)
        if purpose != "post-images" and len(payload.files) != 1:
            raise HTTPException(422, "Choose exactly one image")
        if purpose == "article-images" and len(target.inline_image_keys) >= 30:
            raise HTTPException(422, "An article can contain up to 30 inline images")
        limit = self.max_size(purpose)
        if any(file.size_bytes > limit for file in payload.files):
            raise HTTPException(413, "Image exceeds the configured size limit")
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
                get_resources(request).s3_public.generate_presigned_url, "put_object",
                Params={"Bucket": upload.bucket, "Key": file.temporary_key, "ContentType": file.content_type},
                ExpiresIn=settings.upload_expiry_seconds, HttpMethod="PUT",
            )
            instructions.append(PresignedImageFile(upload_url=url, headers={"Content-Type": file.content_type}, max_size_bytes=limit))
        async with transaction(get_resources(request).mongo) as db_session:
            await upload.insert(session=db_session)
            for file in upload.files:
                await queue_deletion(upload.bucket, file.temporary_key, not_before=upload.expires_at + timedelta(hours=1), session=db_session)
        return ImageUploadResponse(upload_id=str(upload.id), expires_at=upload.expires_at, files=instructions)

    async def _copy_and_validate(self, request: Request, upload: ImageUpload, keys: list[str]) -> None:
        client = get_resources(request).s3
        for file, key in zip(upload.files, keys, strict=True):
            try:
                await asyncio.to_thread(
                    client.copy_object, Bucket=upload.bucket, Key=key,
                    CopySource={"Bucket": upload.bucket, "Key": file.temporary_key},
                    MetadataDirective="REPLACE", ContentType=file.content_type,
                )
            except ClientError as exc:
                if exc.response["Error"]["Code"] in {"NoSuchKey", "404", "NotFound"}:
                    raise HTTPException(409, "Upload all files before confirming") from exc
                raise
            info = await asyncio.to_thread(client.head_object, Bucket=upload.bucket, Key=key)
            if info["ContentLength"] > self.max_size(upload.purpose):
                raise HTTPException(413, "Image exceeds the configured size limit")
            if info["ContentLength"] != file.size_bytes:
                raise HTTPException(422, "Uploaded size does not match the requested size")
            result = await asyncio.to_thread(client.get_object, Bucket=upload.bucket, Key=key, Range="bytes=0-11")
            body = result["Body"]
            try:
                signature = await asyncio.to_thread(body.read, 12)
            finally:
                body.close()
            if image_type(signature) != (file.content_type, EXTENSIONS[file.content_type]):
                raise HTTPException(415, "Use JPEG, PNG, or WebP bytes matching the requested content type")

    async def complete(self, request: Request, owner: User, purpose: ImagePurpose, target_id: str, upload_id: str) -> dict[str, Any]:
        try:
            return await self._complete(request, owner, purpose, target_id, upload_id)
        except (HTTPException, ApplicationError):
            raise
        except Exception as exc:
            logger.exception("Failed to confirm image upload")
            raise HTTPException(503, "Image storage or database is unavailable; retry confirmation") from exc

    async def _complete(self, request: Request, owner: User, purpose: ImagePurpose, target_id: str, upload_id: str) -> dict[str, Any]:
        await self.target(purpose, target_id, owner)
        if not PydanticObjectId.is_valid(upload_id):
            raise HTTPException(404, "Upload not found")
        upload = await ImageUpload.get(PydanticObjectId(upload_id))
        if upload is None or upload.owner_id != owner.id or upload.purpose != purpose or upload.target_id != PydanticObjectId(target_id):
            raise HTTPException(404, "Upload not found")
        if upload.status == "completed":
            return upload.result
        now = datetime.now(UTC)
        if upload.expires_at <= now:
            raise HTTPException(409, "Upload has expired; request new upload URLs")
        token = uuid4().hex
        claim = await ImageUpload.find_one({
            "_id": upload.id, "expires_at": {"$gt": now},
            "$or": [{"status": "pending"}, {"status": "processing", "lease_until": {"$lte": now}}],
        }).update({"$set": {"status": "processing", "lease_token": token, "lease_until": now + timedelta(minutes=5)}})
        if claim.modified_count != 1:
            current = await ImageUpload.get(upload.id)
            if current is not None and current.status == "completed":
                return current.result
            raise HTTPException(409, "Upload confirmation is already in progress")
        keys = [f"{purpose}/{uuid4().hex}.{EXTENSIONS[file.content_type]}" for file in upload.files]
        try:
            for key in keys:
                await queue_deletion(upload.bucket, key, not_before=now + timedelta(hours=1))
            await self._copy_and_validate(request, upload, keys)
            result = await self._attach(request, owner, upload, keys, token)
        except Exception as exc:
            await ImageUpload.find_one({"_id": upload.id, "status": "processing", "lease_token": token}).update(
                {"$set": {"status": "pending", "lease_token": None, "lease_until": None}}
            )
            # Keep cleanup records until a committed attachment can be ruled out.
            if isinstance(exc, (HTTPException, ApplicationError)):
                await ObjectCleanup.find({"bucket": upload.bucket, "key": {"$in": keys}}).update(
                    {"$set": {"not_before": datetime.now(UTC)}}
                )
                raise
            if isinstance(exc, OperationFailure) and exc.has_error_label("TransientTransactionError"):
                raise HTTPException(409, "The resource changed; retry confirmation") from exc
            logger.exception("Image upload confirmation failed")
            raise HTTPException(503, "Image storage or database is unavailable; retry confirmation") from exc
        try:
            await get_resources(request).redis.incr("feed:public:version")
        except Exception:
            logger.warning("Failed to invalidate the public feed after an image update")
        return result

    async def _attach(self, request: Request, owner: User, upload: ImageUpload, keys: list[str], token: str) -> dict[str, Any]:
        async with transaction(get_resources(request).mongo) as db_session:
            current = await ImageUpload.get(upload.id, session=db_session)
            if current is None or current.status != "processing" or current.lease_token != token or current.lease_until is None or current.lease_until <= datetime.now(UTC):
                raise HTTPException(409, "Confirmation lease expired; retry confirmation")
            target = await self.target(upload.purpose, str(upload.target_id), owner, session=db_session)
            old_keys = []
            if upload.purpose == "avatars":
                old_keys = [target.avatar_key] if target.avatar_key else []
                target.avatar_key = keys[0]
                target.avatar_content_type = upload.files[0].content_type
                target.revision += 1
                action, target_type = "AVATAR_CHANGED", "user"
            elif upload.purpose == "post-images":
                old_keys = target.image_keys
                target.image_keys = keys
                action, target_type = "MICRO_POST_IMAGES_CHANGED", "micro_post"
            elif upload.purpose == "article-covers":
                old_keys = [target.thumbnail_key] if target.thumbnail_key else []
                target.thumbnail_key = keys[0]
                action, target_type = "ARTICLE_THUMBNAIL_CHANGED", "article"
            else:
                if len(target.inline_image_keys) >= 30:
                    raise HTTPException(422, "An article can contain up to 30 inline images")
                target.inline_image_keys.append(keys[0])
                action, target_type = "ARTICLE_IMAGE_ADDED", "article"
            target.updated_at = datetime.now(UTC)
            await target.save(session=db_session)
            await record_audit(audit_context(request), action, actor_id=owner.id, target_type=target_type, target_id=str(target.id), metadata={"image_count": len(keys)}, session=db_session)
            if upload.purpose == "avatars":
                response = await ProfileService().response(target, owner.id)
                result = response.model_dump(mode="json")
            elif upload.purpose == "post-images":
                result = (await ContentService().post_response(target)).model_dump(mode="json")
            elif upload.purpose == "article-covers":
                result = (await ContentService().article_response(target)).model_dump(mode="json")
            else:
                result = {"url": publication_image_url(keys[0], "article-images"), "alt_text": upload.files[0].filename}
            current.status = "completed"
            current.result = result
            current.lease_token = None
            current.lease_until = None
            await current.save(session=db_session)
            await ObjectCleanup.find({"bucket": upload.bucket, "key": {"$in": keys}}).delete(session=db_session)
            for key in old_keys:
                await queue_deletion(upload.bucket, key, session=db_session)
        return result
