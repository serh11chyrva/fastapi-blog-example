from datetime import UTC, datetime
import re
from uuid import uuid4

from beanie import PydanticObjectId
from fastapi import APIRouter, File, HTTPException, Query, Request, Response, UploadFile, status
from pymongo.errors import DuplicateKeyError

from backend.core.audit import record_audit
from backend.core.config import get_settings
from backend.core.dependencies import CurrentUser, OptionalUser
from backend.content.schemas import FeedItem
from backend.content.repository import ContentRepository
from backend.content.urls import article_thumbnail_url, share_path
from backend.profiles.models import Follow, User
from backend.profiles.repository import ProfileRepository
from backend.profiles.schemas import ProfileResponse, ProfileUpdate, ProfileUserResponse
from backend.profiles.service import ProfileService
from backend.storage.s3 import delete_avatar, get_avatar, put_avatar


router = APIRouter(tags=["profiles"])
profile_service = ProfileService()
content_repository = ContentRepository()


def _avatar_url(user: User) -> str | None:
    return profile_service.avatar_url(user)


async def _profile_response(user: User, viewer_id: PydanticObjectId | None) -> ProfileResponse:
    return await profile_service.response(user, viewer_id)


def _user_card(user: User) -> ProfileUserResponse:
    return profile_service.user_card(user)


def _avatar_type(data: bytes) -> tuple[str, str] | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None


@router.get("/users/{username}", response_model=ProfileResponse)
async def get_profile(username: str, current_user: OptionalUser) -> ProfileResponse:
    user = await ProfileRepository.find_by_username(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return await _profile_response(user, current_user.id if current_user else None)


@router.get("/users/{username}/publications", response_model=list[FeedItem])
async def list_profile_publications(username: str, kind: str = Query(default="all", pattern="^(all|micro_post|article)$")) -> list[FeedItem]:
    user = await ProfileRepository.find_by_username(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    pairs = await content_repository.list_publications(user.id, kind)
    pairs.sort(key=lambda pair: (pair[2], pair[0], str(pair[1].id)), reverse=True)
    return [
        FeedItem(
            id=str(item.id),
            kind=item_kind,
            share_url=share_path(user.username, item.title if item_kind == "article" else item.text, item.share_id),
            title=item.title if item_kind == "article" else None,
            text=item.text if item_kind == "micro_post" else None,
            summary=item.summary if item_kind == "article" else None,
            thumbnail_url=article_thumbnail_url(item.thumbnail_key) if item_kind == "article" else None,
            author_id=str(user.id),
            author_username=user.username,
            author_display_name=user.display_name,
            author_avatar_url=_avatar_url(user),
            published_at=published_at,
        )
        for item_kind, item, published_at in pairs[:50]
    ]


@router.patch("/me/profile", response_model=ProfileResponse)
async def update_profile(payload: ProfileUpdate, request: Request, current_user: CurrentUser) -> ProfileResponse:
    changes = payload.model_dump(exclude_unset=True)
    if "links" in changes and changes["links"] is not None:
        changes["links"] = [item.model_dump() for item in payload.links or []]
    for field, value in changes.items():
        if value is not None:
            setattr(current_user, field, value)
    current_user.updated_at = datetime.now(UTC)
    client = request.app.state.mongo_client
    async with client.start_session() as db_session:
        async with await db_session.start_transaction():
            await current_user.save(session=db_session)
            await record_audit(
                request,
                "PROFILE_UPDATED",
                actor_id=current_user.id,
                target_type="user",
                target_id=str(current_user.id),
                metadata={"fields": sorted(changes.keys())},
                session=db_session,
            )
    return await _profile_response(current_user, current_user.id)


@router.put("/me/avatar", response_model=ProfileResponse)
async def upload_avatar(request: Request, current_user: CurrentUser, file: UploadFile = File(...)) -> ProfileResponse:
    settings = get_settings()
    data = await file.read(settings.avatar_max_bytes + 1)
    if len(data) > settings.avatar_max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Avatar is too large")
    detected = _avatar_type(data)
    if detected is None:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Use a JPEG, PNG, or WebP image")
    content_type, extension = detected
    new_key = f"avatars/{uuid4().hex}.{extension}"
    client = request.app.state.s3_client
    try:
        await put_avatar(client, settings.avatar_bucket, new_key, data, content_type)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Avatar storage is unavailable") from exc

    old_key = current_user.avatar_key
    current_user.avatar_key = new_key
    current_user.avatar_content_type = content_type
    current_user.updated_at = datetime.now(UTC)
    mongo_client = request.app.state.mongo_client
    try:
        async with mongo_client.start_session() as db_session:
            async with await db_session.start_transaction():
                await current_user.save(session=db_session)
                await record_audit(request, "AVATAR_CHANGED", actor_id=current_user.id, target_type="user", target_id=str(current_user.id), session=db_session)
    except Exception:
        await delete_avatar(client, settings.avatar_bucket, new_key)
        raise
    if old_key:
        try:
            await delete_avatar(client, settings.avatar_bucket, old_key)
        except Exception:
            request.app.state.logger.exception("Failed to remove replaced avatar object")
    return await _profile_response(current_user, current_user.id)


@router.get("/media/avatars/{object_name}")
async def read_avatar(object_name: str, request: Request) -> Response:
    if not re.fullmatch(r"[0-9a-f]{32}\.(jpg|png|webp)", object_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")
    key = f"avatars/{object_name}"
    user = await User.find_one(User.avatar_key == key)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")
    try:
        result = await get_avatar(request.app.state.s3_client, get_settings().avatar_bucket, key)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Avatar storage is unavailable") from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")
    data, content_type = result
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"})


@router.get("/users/{username}/followers", response_model=list[ProfileUserResponse])
async def list_followers(username: str) -> list[ProfileUserResponse]:
    user = await ProfileRepository.find_by_username(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    follows = await Follow.find(Follow.followee_id == user.id).sort(-Follow.created_at).to_list()
    users = await ProfileRepository.users_by_ids([item.follower_id for item in follows])
    by_id = {item.id: item for item in users}
    return [_user_card(by_id[item.follower_id]) for item in follows if item.follower_id in by_id]


@router.get("/users/{username}/following", response_model=list[ProfileUserResponse])
async def list_following(username: str) -> list[ProfileUserResponse]:
    user = await ProfileRepository.find_by_username(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    follows = await Follow.find(Follow.follower_id == user.id).sort(-Follow.created_at).to_list()
    users = await ProfileRepository.users_by_ids([item.followee_id for item in follows])
    by_id = {item.id: item for item in users}
    return [_user_card(by_id[item.followee_id]) for item in follows if item.followee_id in by_id]


@router.put("/users/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def follow_user(username: str, request: Request, current_user: CurrentUser) -> Response:
    user = await ProfileRepository.find_by_username(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot follow yourself")
    existing = await Follow.find_one(Follow.follower_id == current_user.id, Follow.followee_id == user.id)
    if existing is None:
        client = request.app.state.mongo_client
        try:
            async with client.start_session() as db_session:
                async with await db_session.start_transaction():
                    await Follow(follower_id=current_user.id, followee_id=user.id, created_at=datetime.now(UTC)).insert(session=db_session)
                    await record_audit(request, "USER_FOLLOWED", actor_id=current_user.id, target_type="user", target_id=str(user.id), session=db_session)
        except DuplicateKeyError:
            pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/users/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(username: str, request: Request, current_user: CurrentUser) -> Response:
    user = await ProfileRepository.find_by_username(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    existing = await Follow.find_one(Follow.follower_id == current_user.id, Follow.followee_id == user.id)
    if existing is not None:
        client = request.app.state.mongo_client
        async with client.start_session() as db_session:
            async with await db_session.start_transaction():
                await existing.delete(session=db_session)
                await record_audit(request, "USER_UNFOLLOWED", actor_id=current_user.id, target_type="user", target_id=str(user.id), session=db_session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
