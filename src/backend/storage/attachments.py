"""Ownership checks and domain attachment changes used by the upload protocol."""

from dataclasses import dataclass
from datetime import UTC, datetime

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.content.models import Article, MicroPost
from backend.content.presenters import article_response, post_response
from backend.content.schemas import ArticleImageResponse, ArticleResponse, MicroPostResponse
from backend.content.urls import publication_image_url
from backend.core.errors import InvalidOperation, NotFound
from backend.profiles.models import User
from backend.profiles.queries import ProfileQueries
from backend.profiles.schemas import ProfileResponse
from backend.storage.models import ImagePurpose, ImageUpload


type UploadResult = ProfileResponse | MicroPostResponse | ArticleResponse | ArticleImageResponse


@dataclass(frozen=True, slots=True)
class AttachmentResult:
    response: UploadResult
    replaced_keys: list[str]


class ImageAttachments:
    async def target(self, purpose: ImagePurpose, target_id: str, owner: User, *, session: AsyncClientSession | None = None) -> User | MicroPost | Article:
        if not PydanticObjectId.is_valid(target_id):
            raise NotFound("Resource not found")
        object_id = PydanticObjectId(target_id)
        if purpose == "avatars":
            user = await User.get(object_id, session=session)
            if user is None or user.id != owner.id:
                raise NotFound("Resource not found")
            return user
        publication = await MicroPost.get(object_id, session=session) if purpose == "post-images" else await Article.get(object_id, session=session)
        if publication is None or publication.deleted_at is not None or publication.author_id != owner.id:
            raise NotFound("Resource not found")
        return publication

    async def apply(self, upload: ImageUpload, keys: list[str], owner: User, audit: AuditContext, session: AsyncClientSession) -> AttachmentResult:
        """Mutate a freshly read target and audit it inside the caller's transaction."""
        target = await self.target(upload.purpose, str(upload.target_id), owner, session=session)
        old_keys: list[str] = []
        if isinstance(target, User):
            old_keys = [target.avatar_key] if target.avatar_key else []
            target.avatar_key = keys[0]
            target.avatar_content_type = upload.files[0].content_type
            target.revision += 1
            action, target_type = "AVATAR_CHANGED", "user"
        elif isinstance(target, MicroPost):
            old_keys = target.image_keys
            target.image_keys = keys
            action, target_type = "MICRO_POST_IMAGES_CHANGED", "micro_post"
        elif upload.purpose == "article-covers":
            old_keys = [target.thumbnail_key] if target.thumbnail_key else []
            target.thumbnail_key = keys[0]
            action, target_type = "ARTICLE_THUMBNAIL_CHANGED", "article"
        else:
            if len(target.inline_image_keys) >= 30:
                raise InvalidOperation("An article can contain up to 30 inline images")
            target.inline_image_keys.append(keys[0])
            action, target_type = "ARTICLE_IMAGE_ADDED", "article"
        target.updated_at = datetime.now(UTC)
        await target.save(session=session)
        await record_audit(audit, action, actor_id=owner.id, target_type=target_type, target_id=str(target.id), metadata={"image_count": len(keys)}, session=session)
        response: UploadResult
        if isinstance(target, User):
            response = await ProfileQueries().response(target, owner.id)
        elif isinstance(target, MicroPost):
            response = post_response(target, owner)
        elif upload.purpose == "article-covers":
            response = article_response(target, owner)
        else:
            response = ArticleImageResponse(url=publication_image_url(keys[0], "article-images"), alt_text=upload.files[0].filename)
        return AttachmentResult(response, old_keys)


def saved_result(upload: ImageUpload) -> UploadResult:
    """Validate a completed result according to the immutable upload purpose."""
    if upload.result is None:
        raise InvalidOperation("Completed upload result is missing")
    if upload.purpose == "avatars":
        return ProfileResponse.model_validate(upload.result)
    if upload.purpose == "post-images":
        return MicroPostResponse.model_validate(upload.result)
    if upload.purpose == "article-covers":
        return ArticleResponse.model_validate(upload.result)
    return ArticleImageResponse.model_validate(upload.result)
