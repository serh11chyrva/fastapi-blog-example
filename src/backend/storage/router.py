from typing import Any

from fastapi import APIRouter, Request, status

from backend.content.schemas import ArticleImageResponse, ArticleResponse, MicroPostResponse
from backend.core.dependencies import CurrentUser
from backend.profiles.schemas import ProfileResponse
from backend.storage.schemas import ImageUploadRequest, ImageUploadResponse
from backend.storage.service import ImageStorageService


router = APIRouter(tags=["Media"])
service = ImageStorageService()


@router.post("/me/avatar/uploads", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED, summary="Prepare an avatar upload")
async def prepare_avatar(payload: ImageUploadRequest, request: Request, current_user: CurrentUser) -> ImageUploadResponse:
    return await service.create(request, current_user, "avatars", str(current_user.id), payload)


@router.post("/me/avatar/uploads/{upload_id}/complete", response_model=ProfileResponse, summary="Confirm an avatar upload")
async def complete_avatar(upload_id: str, request: Request, current_user: CurrentUser) -> dict[str, Any]:
    return await service.complete(request, current_user, "avatars", str(current_user.id), upload_id)


@router.post("/posts/{post_id}/images/uploads", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED, summary="Prepare a post gallery upload")
async def prepare_post_images(post_id: str, payload: ImageUploadRequest, request: Request, current_user: CurrentUser) -> ImageUploadResponse:
    return await service.create(request, current_user, "post-images", post_id, payload)


@router.post("/posts/{post_id}/images/uploads/{upload_id}/complete", response_model=MicroPostResponse, summary="Confirm replacement of a post gallery")
async def complete_post_images(post_id: str, upload_id: str, request: Request, current_user: CurrentUser) -> dict[str, Any]:
    return await service.complete(request, current_user, "post-images", post_id, upload_id)


@router.post("/articles/{article_id}/cover/uploads", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED, summary="Prepare an article cover upload")
async def prepare_cover(article_id: str, payload: ImageUploadRequest, request: Request, current_user: CurrentUser) -> ImageUploadResponse:
    return await service.create(request, current_user, "article-covers", article_id, payload)


@router.post("/articles/{article_id}/cover/uploads/{upload_id}/complete", response_model=ArticleResponse, summary="Confirm replacement of an article cover")
async def complete_cover(article_id: str, upload_id: str, request: Request, current_user: CurrentUser) -> dict[str, Any]:
    return await service.complete(request, current_user, "article-covers", article_id, upload_id)


@router.post("/articles/{article_id}/images/uploads", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED, summary="Prepare an inline article image upload")
async def prepare_article_image(article_id: str, payload: ImageUploadRequest, request: Request, current_user: CurrentUser) -> ImageUploadResponse:
    return await service.create(request, current_user, "article-images", article_id, payload)


@router.post("/articles/{article_id}/images/uploads/{upload_id}/complete", response_model=ArticleImageResponse, summary="Confirm an inline article image upload")
async def complete_article_image(article_id: str, upload_id: str, request: Request, current_user: CurrentUser) -> dict[str, Any]:
    return await service.complete(request, current_user, "article-images", article_id, upload_id)
