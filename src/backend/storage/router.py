from typing import Annotated
from backend.audit.dependencies import Audit
from backend.core.resources import Resources

from fastapi import APIRouter, Depends, Response, status

from backend.content.schemas import ArticleImageResponse, ArticleResponse, MicroPostResponse
from backend.auth.dependencies import CurrentUser
from backend.profiles.schemas import OwnProfileResponse
from backend.profiles.queries import ProfileQueries
from backend.storage.schemas import ImageUploadRequest, ImageUploadResponse
from backend.storage.service import ImageStorageService


router = APIRouter(tags=["Media"])
def image_service(resources: Resources, audit: Audit) -> ImageStorageService:
    return ImageStorageService(resources, audit)


Storage = Annotated[ImageStorageService, Depends(image_service)]


@router.post("/me/avatar/uploads", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED, summary="Prepare an avatar upload")
async def prepare_avatar(payload: ImageUploadRequest, service: Storage, current_user: CurrentUser) -> ImageUploadResponse:
    return await service.create(current_user, "avatars", str(current_user.id), payload)


@router.post("/me/avatar/uploads/{upload_id}/complete", response_model=OwnProfileResponse, summary="Confirm an avatar upload")
async def complete_avatar(upload_id: str, service: Storage, response: Response, current_user: CurrentUser) -> OwnProfileResponse:
    await service.complete(current_user, "avatars", str(current_user.id), upload_id)
    response.headers["Cache-Control"] = "private, no-store"
    return await ProfileQueries().own_by_id(current_user.id)


@router.post("/posts/{post_id}/images/uploads", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED, summary="Prepare a post gallery upload")
async def prepare_post_images(post_id: str, payload: ImageUploadRequest, service: Storage, current_user: CurrentUser) -> ImageUploadResponse:
    return await service.create(current_user, "post-images", post_id, payload)


@router.post("/posts/{post_id}/images/uploads/{upload_id}/complete", response_model=MicroPostResponse, summary="Confirm replacement of a post gallery")
async def complete_post_images(post_id: str, upload_id: str, service: Storage, current_user: CurrentUser) -> MicroPostResponse:
    result = await service.complete(current_user, "post-images", post_id, upload_id)
    return MicroPostResponse.model_validate(result.model_dump())


@router.post("/articles/{article_id}/cover/uploads", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED, summary="Prepare an article cover upload")
async def prepare_cover(article_id: str, payload: ImageUploadRequest, service: Storage, current_user: CurrentUser) -> ImageUploadResponse:
    return await service.create(current_user, "article-covers", article_id, payload)


@router.post("/articles/{article_id}/cover/uploads/{upload_id}/complete", response_model=ArticleResponse, summary="Confirm replacement of an article cover")
async def complete_cover(article_id: str, upload_id: str, service: Storage, current_user: CurrentUser) -> ArticleResponse:
    result = await service.complete(current_user, "article-covers", article_id, upload_id)
    return ArticleResponse.model_validate(result.model_dump())


@router.post("/articles/{article_id}/images/uploads", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED, summary="Prepare an inline article image upload")
async def prepare_article_image(article_id: str, payload: ImageUploadRequest, service: Storage, current_user: CurrentUser) -> ImageUploadResponse:
    return await service.create(current_user, "article-images", article_id, payload)


@router.post("/articles/{article_id}/images/uploads/{upload_id}/complete", response_model=ArticleImageResponse, summary="Confirm an inline article image upload")
async def complete_article_image(article_id: str, upload_id: str, service: Storage, current_user: CurrentUser) -> ArticleImageResponse:
    result = await service.complete(current_user, "article-images", article_id, upload_id)
    return ArticleImageResponse.model_validate(result.model_dump())
