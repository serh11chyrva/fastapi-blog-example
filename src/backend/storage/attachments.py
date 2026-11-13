"""Ownership checks and domain attachment changes used by the upload protocol."""

from dataclasses import dataclass
from datetime import UTC, datetime

from beanie import PydanticObjectId
from pymongo.asynchronous.client_session import AsyncClientSession

from backend.articles.models import Article
from backend.articles.presenters import article_response
from backend.articles.schemas import ArticleImageResponse, ArticleResponse
from backend.audit.context import AuditContext
from backend.audit.service import record_audit
from backend.core.errors import InvalidOperation, NotFound
from backend.posts.models import MicroPost
from backend.posts.content import validate_post_content
from backend.publications.access import readable_publication
from backend.posts.presenters import post_response
from backend.posts.schemas import MicroPostResponse
from backend.profiles.models import AvatarImage, User
from backend.profiles.queries import ProfileQueries
from backend.profiles.schemas import ProfileResponse
from backend.publications.attachments import GifAttachment, ImageAttachment
from backend.publications.queries import load_authors
from backend.storage.models import ImagePurpose, ImageUpload
from backend.storage.urls import publication_image_url

type UploadResult = ProfileResponse | MicroPostResponse | ArticleResponse | ArticleImageResponse


@dataclass(frozen=True, slots=True)
class AttachmentResult:
    """Completed attachment response and the image keys it replaced."""

    response: UploadResult
    replaced_keys: list[str]


class ImageAttachments:
    """Ownership checks and transactional changes to image attachment targets."""

    async def target(
        self,
        purpose: ImagePurpose,
        target_id: str,
        owner: User,
        *,
        session: AsyncClientSession | None = None,
    ) -> User | MicroPost | Article:
        """Load an upload target and enforce ownership and deletion rules.

        :param purpose: Immutable image purpose selecting target rules and size limits.
        :param target_id: Identifier of the resource targeted by the operation.
        :param owner: Authenticated account owning or initiating the operation.
        :param session: Optional MongoDB session for the operation or caller
            transaction.
        :return: The owned user, micro-post, or article document.
        """
        if not PydanticObjectId.is_valid(target_id):
            raise NotFound("Resource not found")

        object_id = PydanticObjectId(target_id)

        if purpose in {"avatars", "profile-banners"}:
            user = await User.get(object_id, session=session)

            if user is None or user.id != owner.id:
                raise NotFound("Resource not found")

            return user

        publication = (
            await MicroPost.get(object_id, session=session)
            if purpose == "post-images"
            else await Article.get(object_id, session=session)
        )

        if publication is None or publication.deleted_at is not None or publication.owner_id != owner.id:
            raise NotFound("Resource not found")

        if isinstance(publication, MicroPost) and publication.reply is not None and publication.archived_at is None:
            await readable_publication(
                "micro_post", str(publication.id), owner.id, session, touch=session is not None,
            )
        return publication

    async def apply(
        self,
        upload: ImageUpload,
        keys: list[str],
        owner: User,
        audit: AuditContext,
        session: AsyncClientSession,
    ) -> AttachmentResult:
        """Mutate a freshly read target and audit it inside the caller's transaction.

        :param upload: Persisted upload session and its immutable file metadata.
        :param keys: Final object keys corresponding to the upload files in order.
        :param owner: Authenticated account owning or initiating the operation.
        :param audit: Request metadata attached to audited operations.
        :param session: MongoDB session for the caller transaction.
        :return: The attachment response and the keys of replaced images.
        """
        target = await self.target(upload.purpose, str(upload.target_id), owner, session=session)
        old_keys: list[str] = []

        if isinstance(target, User):
            image = AvatarImage(key=keys[0], content_type=upload.files[0].content_type)
            if upload.purpose == "profile-banners":
                old_keys = [target.banner.key] if target.banner else []
                target.banner = image
                action = "PROFILE_BANNER_CHANGED"
            else:
                old_keys = [target.avatars.original.key] if target.avatars.original else []
                target.avatars.original = image
                action = "AVATAR_CHANGED"

            target.revision += 1
            target_type = "user"
        elif isinstance(target, MicroPost):
            old_keys = target.image_keys
            target.image_keys = keys
            target.attachments = [
                item for item in target.attachments if not isinstance(item, (ImageAttachment, GifAttachment))
            ]
            validate_post_content(target.text, target.attachments, target.image_keys)
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
        await record_audit(
            audit,
            action,
            actor_id=owner.id,
            target_type=target_type,
            target_id=str(target.id),
            metadata={"image_count": len(keys)},
            session=session,
        )
        response: UploadResult

        if isinstance(target, User):
            response = await ProfileQueries().response(target, owner.id)
        elif isinstance(target, MicroPost):
            response = post_response(target, await load_authors(target.author_ids))
        elif upload.purpose == "article-covers":
            response = article_response(target, await load_authors(target.author_ids))
        else:
            response = ArticleImageResponse(
                url=publication_image_url(keys[0], "article-images"),
                alt_text=upload.files[0].filename,
            )

        return AttachmentResult(response, old_keys)


def saved_result(upload: ImageUpload) -> UploadResult:
    """Validate a completed result according to the immutable upload purpose.

    :param upload: Persisted upload session and its immutable file metadata.
    :return: The typed response saved by the completed upload.
    """
    if upload.result is None:
        raise InvalidOperation("Completed upload result is missing")

    if upload.purpose in {"avatars", "profile-banners"}:
        return ProfileResponse.model_validate(upload.result)

    if upload.purpose == "post-images":
        return MicroPostResponse.model_validate(upload.result)

    if upload.purpose == "article-covers":
        return ArticleResponse.model_validate(upload.result)

    return ArticleImageResponse.model_validate(upload.result)
