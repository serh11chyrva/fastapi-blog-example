from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from backend.audit.dependencies import Audit
from backend.auth.dependencies import CurrentUser
from backend.content.schemas import ArticleImageResponse, ArticleResponse, MicroPostResponse
from backend.core.api_metadata import documented_responses, Origin, PostId, ArticleId, UploadId
from backend.core.resources import Resources
from backend.profiles.queries import ProfileQueries
from backend.profiles.schemas import OwnProfileResponse
from backend.storage.schemas import ImageUploadRequest, ImageUploadResponse
from backend.storage.service import ImageStorageService


router = APIRouter()
def image_service(resources: Resources, audit: Audit) -> ImageStorageService:
    return ImageStorageService(resources, audit)


Storage = Annotated[ImageStorageService, Depends(image_service)]


@router.post(
    "/me/avatar/uploads",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prepare an avatar upload",
    description=(
        'Send JSON metadata for ten-minute presigned PUT URLs. Upload raw bytes using '
        'returned headers without application cookies, then confirm. One file is required '
        'except post galleries allow one to five. JPEG, PNG, and WebP allow 5 MiB, or 10 MiB '
        'for covers. Articles allow 30 inline images. Preparation leaves attachments '
        'unchanged.'
    ),
    tags=['Media'],
    responses=documented_responses(401, 403, 409, 413, 503),
)
async def prepare_avatar(
    _origin: Origin,
    payload: ImageUploadRequest,
    service: Storage,
    current_user: CurrentUser,
) -> ImageUploadResponse:
    return await service.create(current_user, "avatars", str(current_user.id), payload)


@router.post(
    "/me/avatar/uploads/{upload_id}/complete",
    response_model=OwnProfileResponse,
    summary="Confirm an avatar upload",
    description=(
        'Confirm all files, validate exact size and image signatures, and attach immutable '
        'final objects. Requires ownership. Replays return the saved typed result without '
        'attaching again. Galleries replace the existing images; inline article uploads '
        'append one image. Completion uses a five-minute lease and requires starting before '
        'upload expiry. Avatar attachment increments revision once. Every HTTP response '
        'returns the current own profile and revision with private, no-store, including '
        'replay.'
    ),
    tags=['Media'],
    responses=documented_responses(401, 403, 404, 409, 413, 415, 422, 503),
)
async def complete_avatar(
    _origin: Origin,
    upload_id: UploadId,
    service: Storage,
    response: Response,
    current_user: CurrentUser,
) -> OwnProfileResponse:
    await service.complete(current_user, "avatars", str(current_user.id), upload_id)
    response.headers["Cache-Control"] = "private, no-store"
    return await ProfileQueries().own_by_id(current_user.id)


@router.post(
    "/posts/{post_id}/images/uploads",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prepare a post gallery upload",
    description=(
        'Send JSON metadata for ten-minute presigned PUT URLs. Upload raw bytes using '
        'returned headers without application cookies, then confirm. One file is required '
        'except post galleries allow one to five. JPEG, PNG, and WebP allow 5 MiB, or 10 MiB '
        'for covers. Articles allow 30 inline images. Preparation leaves attachments '
        'unchanged.'
    ),
    tags=['Media'],
    responses=documented_responses(401, 403, 404, 409, 413, 503),
)
async def prepare_post_images(
    _origin: Origin,
    post_id: PostId,
    payload: ImageUploadRequest,
    service: Storage,
    current_user: CurrentUser,
) -> ImageUploadResponse:
    return await service.create(current_user, "post-images", post_id, payload)


@router.post(
    "/posts/{post_id}/images/uploads/{upload_id}/complete",
    response_model=MicroPostResponse,
    summary="Confirm replacement of a post gallery",
    description=(
        'Confirm all files, validate exact size and image signatures, and attach immutable '
        'final objects. Requires ownership. Replays return the saved typed result without '
        'attaching again. Galleries replace the existing images; inline article uploads '
        'append one image. Completion uses a five-minute lease and requires starting before '
        'upload expiry.'
    ),
    tags=['Media'],
    responses=documented_responses(401, 403, 404, 409, 413, 415, 422, 503),
)
async def complete_post_images(
    _origin: Origin,
    post_id: PostId,
    upload_id: UploadId,
    service: Storage,
    current_user: CurrentUser,
) -> MicroPostResponse:
    result = await service.complete(current_user, "post-images", post_id, upload_id)
    return MicroPostResponse.model_validate(result.model_dump())


@router.post(
    "/articles/{article_id}/cover/uploads",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prepare an article cover upload",
    description=(
        'Send JSON metadata for ten-minute presigned PUT URLs. Upload raw bytes using '
        'returned headers without application cookies, then confirm. One file is required '
        'except post galleries allow one to five. JPEG, PNG, and WebP allow 5 MiB, or 10 MiB '
        'for covers. Articles allow 30 inline images. Preparation leaves attachments '
        'unchanged.'
    ),
    tags=['Media'],
    responses=documented_responses(401, 403, 404, 409, 413, 503),
)
async def prepare_cover(
    _origin: Origin,
    article_id: ArticleId,
    payload: ImageUploadRequest,
    service: Storage,
    current_user: CurrentUser,
) -> ImageUploadResponse:
    return await service.create(current_user, "article-covers", article_id, payload)


@router.post(
    "/articles/{article_id}/cover/uploads/{upload_id}/complete",
    response_model=ArticleResponse,
    summary="Confirm replacement of an article cover",
    description=(
        'Confirm all files, validate exact size and image signatures, and attach immutable '
        'final objects. Requires ownership. Replays return the saved typed result without '
        'attaching again. Galleries replace the existing images; inline article uploads '
        'append one image. Completion uses a five-minute lease and requires starting before '
        'upload expiry.'
    ),
    tags=['Media'],
    responses=documented_responses(401, 403, 404, 409, 413, 415, 422, 503),
)
async def complete_cover(
    _origin: Origin,
    article_id: ArticleId,
    upload_id: UploadId,
    service: Storage,
    current_user: CurrentUser,
) -> ArticleResponse:
    result = await service.complete(current_user, "article-covers", article_id, upload_id)
    return ArticleResponse.model_validate(result.model_dump())


@router.post(
    "/articles/{article_id}/images/uploads",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prepare an inline article image upload",
    description=(
        'Send JSON metadata for ten-minute presigned PUT URLs. Upload raw bytes using '
        'returned headers without application cookies, then confirm. One file is required '
        'except post galleries allow one to five. JPEG, PNG, and WebP allow 5 MiB, or 10 MiB '
        'for covers. Articles allow 30 inline images. Preparation leaves attachments '
        'unchanged.'
    ),
    tags=['Media'],
    responses=documented_responses(401, 403, 404, 409, 413, 503),
)
async def prepare_article_image(
    _origin: Origin,
    article_id: ArticleId,
    payload: ImageUploadRequest,
    service: Storage,
    current_user: CurrentUser,
) -> ImageUploadResponse:
    return await service.create(current_user, "article-images", article_id, payload)


@router.post(
    "/articles/{article_id}/images/uploads/{upload_id}/complete",
    response_model=ArticleImageResponse,
    summary="Confirm an inline article image upload",
    description=(
        'Confirm all files, validate exact size and image signatures, and attach immutable '
        'final objects. Requires ownership. Replays return the saved typed result without '
        'attaching again. Galleries replace the existing images; inline article uploads '
        'append one image. Completion uses a five-minute lease and requires starting before '
        'upload expiry.'
    ),
    tags=['Media'],
    responses=documented_responses(401, 403, 404, 409, 413, 415, 422, 503),
)
async def complete_article_image(
    _origin: Origin,
    article_id: ArticleId,
    upload_id: UploadId,
    service: Storage,
    current_user: CurrentUser,
) -> ArticleImageResponse:
    result = await service.complete(current_user, "article-images", article_id, upload_id)
    return ArticleImageResponse.model_validate(result.model_dump())
