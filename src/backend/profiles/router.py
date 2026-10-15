"""HTTP adapters for public profiles and owner settings."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from backend.audit.dependencies import Audit
from backend.auth.dependencies import CurrentUser, OptionalUser
from backend.content.presenters import feed_item
from backend.content.repository import ContentRepository, FeedKind
from backend.content.schemas import FeedItem
from backend.core.resources import Resources
from backend.profiles.presenters import user_card
from backend.profiles.queries import ProfileQueries
from backend.profiles.repository import ProfileRepository
from backend.profiles.schemas import BadgePreferenceUpdate, OwnProfileResponse, ProfileResponse, ProfileUpdate, ProfileUserResponse
from backend.profiles.service import ProfileService


router = APIRouter(tags=["profiles"])
queries = ProfileQueries()


def get_profile_service(resources: Resources, audit: Audit) -> ProfileService:
    return ProfileService(resources, audit)


Profiles = Annotated[ProfileService, Depends(get_profile_service)]


@router.get("/users/{username}", response_model=ProfileResponse)
async def get_profile(username: str, current_user: OptionalUser) -> ProfileResponse:
    return await queries.response(await queries.by_username(username), current_user.id if current_user else None)


@router.get("/users/{username}/publications", response_model=list[FeedItem])
async def list_profile_publications(username: str, kind: FeedKind = "all", offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=50)) -> list[FeedItem]:
    user = await queries.by_username(username)
    entries = await ContentRepository.list_publications(user.id, kind, offset=offset, limit=limit)
    return [feed_item(entry.publication, user) for entry in entries]


@router.get("/me/profile", response_model=OwnProfileResponse)
async def get_own_profile(current_user: CurrentUser, response: Response) -> OwnProfileResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await queries.own_response(current_user)


@router.patch("/me/profile", response_model=OwnProfileResponse)
async def update_profile(payload: ProfileUpdate, profiles: Profiles, response: Response, current_user: CurrentUser) -> OwnProfileResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await queries.own_response(await profiles.update(current_user.id, payload))


@router.patch("/me/badges/{code}", response_model=OwnProfileResponse)
async def update_badge_preferences(code: str, payload: BadgePreferenceUpdate, profiles: Profiles, response: Response, current_user: CurrentUser) -> OwnProfileResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await queries.own_response(await profiles.update(current_user.id, payload, badge_code=code))


@router.get("/users/{username}/followers", response_model=list[ProfileUserResponse])
async def list_followers(username: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=20, ge=1, le=100)) -> list[ProfileUserResponse]:
    user = await queries.by_username(username)
    return [user_card(item) for item in await ProfileRepository.connections(user.id, "followers", offset, limit)]


@router.get("/users/{username}/following", response_model=list[ProfileUserResponse])
async def list_following(username: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=20, ge=1, le=100)) -> list[ProfileUserResponse]:
    user = await queries.by_username(username)
    return [user_card(item) for item in await ProfileRepository.connections(user.id, "following", offset, limit)]


@router.put("/users/{username}/follow", status_code=204)
async def follow_user(username: str, current_user: CurrentUser, profiles: Profiles) -> Response:
    await profiles.follow(current_user, username)
    return Response(status_code=204)


@router.delete("/users/{username}/follow", status_code=204)
async def unfollow_user(username: str, current_user: CurrentUser, profiles: Profiles) -> Response:
    await profiles.unfollow(current_user, username)
    return Response(status_code=204)
