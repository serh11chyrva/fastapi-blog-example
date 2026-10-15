from backend.core.transactions import transaction
from backend.core.resources import get_resources
from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pymongo.errors import DuplicateKeyError

from backend.audit.service import record_audit
from backend.audit.dependencies import audit_context
from backend.auth.dependencies import CurrentUser, OptionalUser
from backend.content.schemas import FeedItem
from backend.content.repository import ContentRepository
from backend.content.urls import article_thumbnail_url, publication_image_url, share_path
from backend.profiles.models import Follow, User
from backend.profiles.repository import ProfileRepository
from backend.profiles.schemas import BadgePreferenceUpdate, OwnProfileResponse, ProfileResponse, ProfileUpdate, ProfileUserResponse
from backend.profiles.service import ProfileService


router = APIRouter(tags=["profiles"])
profile_service = ProfileService()
content_repository = ContentRepository()


def _avatar_url(user: User) -> str | None:
    return profile_service.avatar_url(user)


async def _profile_response(user: User, viewer_id: PydanticObjectId | None) -> ProfileResponse:
    return await profile_service.response(user, viewer_id)


def _user_card(user: User) -> ProfileUserResponse:
    return profile_service.user_card(user)


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
            images=[publication_image_url(key, "post-images") for key in item.image_keys] if item_kind == "micro_post" else [],
            author_id=str(user.id),
            author_username=user.username,
            author_display_name=user.display_name,
            author_avatar_url=_avatar_url(user),
            published_at=published_at,
        )
        for item_kind, item, published_at in pairs[:50]
    ]


@router.get("/me/profile", response_model=OwnProfileResponse)
async def get_own_profile(current_user: CurrentUser, response: Response) -> OwnProfileResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await profile_service.own_response(current_user)


@router.patch("/me/profile", response_model=OwnProfileResponse)
async def update_profile(payload: ProfileUpdate, request: Request, response: Response, current_user: CurrentUser) -> OwnProfileResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await profile_service.update(request, current_user.id, payload)


@router.patch("/me/badges/{code}", response_model=OwnProfileResponse)
async def update_badge_preferences(code: str, payload: BadgePreferenceUpdate, request: Request, response: Response, current_user: CurrentUser) -> OwnProfileResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await profile_service.update(request, current_user.id, payload, badge_code=code)


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
        client = get_resources(request).mongo
        try:
            async with transaction(client) as db_session:
                await Follow(follower_id=current_user.id, followee_id=user.id, created_at=datetime.now(UTC)).insert(session=db_session)
                await record_audit(audit_context(request), "USER_FOLLOWED", actor_id=current_user.id, target_type="user", target_id=str(user.id), session=db_session)
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
        client = get_resources(request).mongo
        async with transaction(client) as db_session:
            await existing.delete(session=db_session)
            await record_audit(audit_context(request), "USER_UNFOLLOWED", actor_id=current_user.id, target_type="user", target_id=str(user.id), session=db_session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
