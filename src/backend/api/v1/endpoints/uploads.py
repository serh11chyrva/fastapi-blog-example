from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from backend.api.metadata import ArticleId, Origin, PostId, UploadId, documented_responses
from backend.articles.schemas import ArticleImageResponse, ArticleResponse
from backend.audit.dependencies import Audit
from backend.auth.dependencies import CurrentUser
from backend.core.resources import Resources
from backend.links.presentation import hydrate_publications
from backend.posts.schemas import MicroPostResponse
from backend.profiles.queries import ProfileQueries
from backend.profiles.schemas import OwnProfileResponse
from backend.storage.schemas import ImageUploadRequest, ImageUploadResponse
from backend.storage.service import ImageStorageService

router = APIRouter()


def image_service(resources: Resources, audit: Audit) -> ImageStorageService:
    """Create the upload service from request-scoped dependencies.

    :param resources: Application-owned database, cache, and storage clients.
    :param audit: Request metadata attached to audited operations.
    :return: The configured image storage service.
    """
    return ImageStorageService(resources, audit)


Storage = Annotated[ImageStorageService, Depends(image_service)]


@router.post(
    "/me/avatar/uploads",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prepare an avatar upload",
    description=(
        "Send JSON metadata for ten-minute presigned PUT URLs. Upload raw bytes using "
        "returned headers without application cookies, then confirm. One file is required "
        "except post galleries allow one to five. JPEG, PNG, and WebP allow 5 MiB, or 10 MiB "
        "for covers. Articles allow 30 inline images. Preparation leaves attachments "
        "unchanged."
    ),
    tags=["Media"],
    responses=documented_responses(401, 403, 409, 413, 503),
)
async def prepare_avatar(
    _origin: Origin,
    payload: ImageUploadRequest,
    service: Storage,
    current_user: CurrentUser,
) -> ImageUploadResponse:
    """Prepare a direct upload for the current account's avatar.

    :param _origin: Validated Origin header required by mutating API operations.
    :param payload: Validated request data for the operation.
    :param service: Image upload service injected for this request.
    :param current_user: Account resolved from the current session cookie.
    :return: The upload session and presigned PUT instructions.
    """
    return await service.create(current_user, "avatars", str(current_user.id), payload)


@router.post(
    "/me/avatar/uploads/{upload_id}/complete",
    response_model=OwnProfileResponse,
    summary="Confirm an avatar upload",
    description=(
        "Confirm all files, validate exact size and image signatures, and attach immutable "
        "final objects. Requires ownership. Replays return the saved typed result without "
        "attaching again. Galleries replace the existing images; inline article uploads "
        "append one image. Completion uses a five-minute lease and requires starting before "
        "upload expiry. Avatar attachment increments revision once. Every HTTP response "
        "returns the current own profile and revision with private, no-store, including "
        "replay."
    ),
    tags=["Media"],
    responses=documented_responses(401, 403, 404, 409, 413, 415, 422, 503),
)
async def complete_avatar(
    _origin: Origin,
    upload_id: UploadId,
    service: Storage,
    response: Response,
    current_user: CurrentUser,
) -> OwnProfileResponse:
    """Confirm an avatar upload and reload current owner profile settings.

    :param _origin: Validated Origin header required by mutating API operations.
    :param upload_id: Upload session identifier returned by upload preparation.
    :param service: Image upload service injected for this request.
    :param response: HTTP response whose headers, cookies, or status may be updated.
    :param current_user: Account resolved from the current session cookie.
    :return: The current owner profile response.
    """
    await service.complete(current_user, "avatars", str(current_user.id), upload_id)
    response.headers["Cache-Control"] = "private, no-store"

    return await ProfileQueries().own_by_id(current_user.id)


@router.post(
    "/me/banner/uploads", response_model=ImageUploadResponse, status_code=201,
    summary="Prepare a profile banner upload",
    description="Prepare a presigned upload for one JPEG, PNG, or WebP banner up to 5 MiB.",
    tags=["Media"], responses=documented_responses(401, 403, 413, 422, 503),
)
async def prepare_banner(
    _origin: Origin, payload: ImageUploadRequest, service: Storage, current_user: CurrentUser,
) -> ImageUploadResponse:
    """Prepare an image upload bound to the current profile.

    :param _origin: Required same-origin mutation header.
    :param payload: Image metadata for the single banner.
    :param service: Request-scoped image storage service.
    :param current_user: Authenticated owner of the target profile.
    :return: Presigned upload instructions.
    """
    return await service.create(current_user, "profile-banners", str(current_user.id), payload)


@router.post(
    "/me/banner/uploads/{upload_id}/complete", response_model=OwnProfileResponse,
    summary="Confirm replacement of the profile banner",
    description="Attach the validated upload, advance the profile revision, and queue cleanup of the former banner.",
    tags=["Media"], responses=documented_responses(401, 403, 404, 409, 413, 415, 422, 503),
)
async def complete_banner(
    _origin: Origin, upload_id: UploadId, service: Storage, response: Response, current_user: CurrentUser,
) -> OwnProfileResponse:
    """Confirm a banner once and return the current owner profile.

    :param _origin: Required same-origin mutation header.
    :param upload_id: Identifier from banner upload preparation.
    :param service: Request-scoped image storage service.
    :param response: HTTP response for the private cache policy.
    :param current_user: Authenticated owner of the target profile.
    :return: Current profile with the attached banner and revision.
    """
    await service.complete(current_user, "profile-banners", str(current_user.id), upload_id)
    response.headers["Cache-Control"] = "private, no-store"

    return await ProfileQueries().own_by_id(current_user.id)


@router.post(
    "/posts/{post_id}/images/uploads",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prepare a post gallery upload",
    description=(
        "Send JSON metadata for ten-minute presigned PUT URLs. Upload raw bytes using "
        "returned headers without application cookies, then confirm. One file is required "
        "except post galleries allow one to five. JPEG, PNG, and WebP allow 5 MiB, or 10 MiB "
        "for covers. Articles allow 30 inline images. Preparation leaves attachments "
        "unchanged."
    ),
    tags=["Media"],
    responses=documented_responses(401, 403, 404, 409, 413, 503),
)
async def prepare_post_images(
    _origin: Origin,
    post_id: PostId,
    payload: ImageUploadRequest,
    service: Storage,
    current_user: CurrentUser,
) -> ImageUploadResponse:
    """Prepare direct uploads for an owned micro-post's images.

    :param _origin: Validated Origin header required by mutating API operations.
    :param post_id: MongoDB identifier of the micro-post.
    :param payload: Validated request data for the operation.
    :param service: Image upload service injected for this request.
    :param current_user: Account resolved from the current session cookie.
    :return: The upload session and presigned PUT instructions.
    """
    return await service.create(current_user, "post-images", post_id, payload)


@router.post(
    "/posts/{post_id}/images/uploads/{upload_id}/complete",
    response_model=MicroPostResponse,
    summary="Confirm replacement of a post gallery",
    description=(
        "Confirm all files, validate exact size and image signatures, and attach immutable "
        "final objects. Requires ownership. Replays return the saved typed result without "
        "attaching again. Galleries replace the existing images; inline article uploads "
        "append one image. Completion uses a five-minute lease and requires starting before "
        "upload expiry."
    ),
    tags=["Media"],
    responses=documented_responses(401, 403, 404, 409, 413, 415, 422, 503),
)
async def complete_post_images(
    _origin: Origin,
    post_id: PostId,
    upload_id: UploadId,
    service: Storage,
    current_user: CurrentUser,
) -> MicroPostResponse:
    """Confirm uploaded images and replace an owned micro-post's attachments.

    Cached link presentations are attached after access checks; missing metadata is queued, not fetched here.

    :param _origin: Validated Origin header required by mutating API operations.
    :param post_id: MongoDB identifier of the micro-post.
    :param upload_id: Upload session identifier returned by upload preparation.
    :param service: Image upload service injected for this request.
    :param current_user: Account resolved from the current session cookie.
    :return: The updated micro-post response.
    """
    result = await service.complete(current_user, "post-images", post_id, upload_id)

    return await hydrate_publications(
        service.resources.redis,
        MicroPostResponse.model_validate(result.model_dump()),
    )


@router.post(
    "/articles/{article_id}/cover/uploads",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prepare an article cover upload",
    description=(
        "Send JSON metadata for ten-minute presigned PUT URLs. Upload raw bytes using "
        "returned headers without application cookies, then confirm. One file is required "
        "except post galleries allow one to five. JPEG, PNG, and WebP allow 5 MiB, or 10 MiB "
        "for covers. Articles allow 30 inline images. Preparation leaves attachments "
        "unchanged."
    ),
    tags=["Media"],
    responses=documented_responses(401, 403, 404, 409, 413, 503),
)
async def prepare_cover(
    _origin: Origin,
    article_id: ArticleId,
    payload: ImageUploadRequest,
    service: Storage,
    current_user: CurrentUser,
) -> ImageUploadResponse:
    """Prepare a direct upload for an owned article's cover.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param payload: Validated request data for the operation.
    :param service: Image upload service injected for this request.
    :param current_user: Account resolved from the current session cookie.
    :return: The upload session and presigned PUT instructions.
    """
    return await service.create(current_user, "article-covers", article_id, payload)


@router.post(
    "/articles/{article_id}/cover/uploads/{upload_id}/complete",
    response_model=ArticleResponse,
    summary="Confirm replacement of an article cover",
    description=(
        "Confirm all files, validate exact size and image signatures, and attach immutable "
        "final objects. Requires ownership. Replays return the saved typed result without "
        "attaching again. Galleries replace the existing images; inline article uploads "
        "append one image. Completion uses a five-minute lease and requires starting before "
        "upload expiry."
    ),
    tags=["Media"],
    responses=documented_responses(401, 403, 404, 409, 413, 415, 422, 503),
)
async def complete_cover(
    _origin: Origin,
    article_id: ArticleId,
    upload_id: UploadId,
    service: Storage,
    current_user: CurrentUser,
) -> ArticleResponse:
    """Confirm a cover upload and attach it to the owned article.

    Cached link presentations are attached after access checks; missing metadata is queued, not fetched here.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param upload_id: Upload session identifier returned by upload preparation.
    :param service: Image upload service injected for this request.
    :param current_user: Account resolved from the current session cookie.
    :return: The updated article response.
    """
    result = await service.complete(current_user, "article-covers", article_id, upload_id)

    return await hydrate_publications(
        service.resources.redis,
        ArticleResponse.model_validate(result.model_dump()),
    )


@router.post(
    "/articles/{article_id}/images/uploads",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prepare an inline article image upload",
    description=(
        "Send JSON metadata for ten-minute presigned PUT URLs. Upload raw bytes using "
        "returned headers without application cookies, then confirm. One file is required "
        "except post galleries allow one to five. JPEG, PNG, and WebP allow 5 MiB, or 10 MiB "
        "for covers. Articles allow 30 inline images. Preparation leaves attachments "
        "unchanged."
    ),
    tags=["Media"],
    responses=documented_responses(401, 403, 404, 409, 413, 503),
)
async def prepare_article_image(
    _origin: Origin,
    article_id: ArticleId,
    payload: ImageUploadRequest,
    service: Storage,
    current_user: CurrentUser,
) -> ImageUploadResponse:
    """Prepare a direct upload for an owned article's inline image.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param payload: Validated request data for the operation.
    :param service: Image upload service injected for this request.
    :param current_user: Account resolved from the current session cookie.
    :return: The upload session and presigned PUT instructions.
    """
    return await service.create(current_user, "article-images", article_id, payload)


@router.post(
    "/articles/{article_id}/images/uploads/{upload_id}/complete",
    response_model=ArticleImageResponse,
    summary="Confirm an inline article image upload",
    description=(
        "Confirm all files, validate exact size and image signatures, and attach immutable "
        "final objects. Requires ownership. Replays return the saved typed result without "
        "attaching again. Galleries replace the existing images; inline article uploads "
        "append one image. Completion uses a five-minute lease and requires starting before "
        "upload expiry."
    ),
    tags=["Media"],
    responses=documented_responses(401, 403, 404, 409, 413, 415, 422, 503),
)
async def complete_article_image(
    _origin: Origin,
    article_id: ArticleId,
    upload_id: UploadId,
    service: Storage,
    current_user: CurrentUser,
) -> ArticleImageResponse:
    """Confirm and attach an inline image to the owned article.

    :param _origin: Validated Origin header required by mutating API operations.
    :param article_id: MongoDB identifier of the article.
    :param upload_id: Upload session identifier returned by upload preparation.
    :param service: Image upload service injected for this request.
    :param current_user: Account resolved from the current session cookie.
    :return: The inline image URL and alternate text.
    """
    result = await service.complete(current_user, "article-images", article_id, upload_id)

    return ArticleImageResponse.model_validate(result.model_dump())
