"""HTTP adapters for public profiles and owner settings."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from backend.api.metadata import Origin, Username, documented_responses
from backend.audit.dependencies import Audit
from backend.auth.dependencies import CurrentUser, OptionalUser
from backend.content.repository import FeedKind
from backend.content.schemas import FeedItem
from backend.core.resources import Resources
from backend.profiles.queries import ProfileQueries
from backend.profiles.schemas import (
    BadgePreferenceUpdate,
    OwnProfileResponse,
    ProfileResponse,
    ProfileUpdate,
    ProfileUserResponse,
)
from backend.profiles.service import ProfileService

router = APIRouter()
queries = ProfileQueries()


def get_profile_service(resources: Resources, audit: Audit) -> ProfileService:
    return ProfileService(resources, audit)


Profiles = Annotated[ProfileService, Depends(get_profile_service)]


@router.get(
    "/users/{username}",
    response_model=ProfileResponse,
    summary="Get a public profile",
    description=(
        "Username is case-insensitive; follow state is relative to the optional current "
        "session."
    ),
    tags=["Profiles"],
    responses=documented_responses(404, 503),
    openapi_extra={"security": [{}, {"SessionCookie": []}]},
)
async def get_profile(
    username: Username, current_user: OptionalUser
) -> ProfileResponse:
    return await queries.response(
        await queries.by_username(username), current_user.id if current_user else None
    )


@router.get(
    "/users/{username}/publications",
    response_model=list[FeedItem],
    summary="List profile publications",
    description=(
        "Returns up to 50 public micro-posts and published articles, newest first. Offset "
        "defaults to 0; limit defaults to 50 and is capped at 50."
    ),
    tags=["Profiles"],
    responses=documented_responses(404, 503),
)
async def list_profile_publications(
    username: Username,
    kind: FeedKind = "all",
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip; refresh from zero after concurrent list changes.",
    ),
    limit: int = Query(
        default=50, ge=1, le=50, description="Page size from 1 to 50; defaults to 50."
    ),
) -> list[FeedItem]:
    return await queries.publications(username, kind, offset, limit)


@router.get(
    "/me/profile",
    response_model=OwnProfileResponse,
    summary="Get your own profile",
    description=(
        "Returns your profile revision and all your badge assignments, including hidden ones, "
        "with assignment timestamps, preferences, and permissions. Requires your session; "
        "response uses private, no-store. Public profile responses never include these "
        "fields."
    ),
    tags=["Profiles"],
    responses=documented_responses(401, 503),
)
async def get_own_profile(
    current_user: CurrentUser, response: Response
) -> OwnProfileResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await queries.own_response(current_user)


@router.patch(
    "/me/profile",
    response_model=OwnProfileResponse,
    summary="Update your profile",
    description=(
        "Send the required revision from GET /me/profile; stale revisions and concurrent "
        "writes return 409. Omitted or null editable fields stay unchanged. Links replace the "
        "list (at most eight). Explicit IDs retain identity; entries without an ID reuse an "
        "unambiguous existing exact-URL match, otherwise get a new UUID. Duplicate, foreign, "
        "or ambiguous IDs return 422. Returns your updated own profile and revision with "
        "private, no-store. Badge visibility uses /me/badges/{code}."
    ),
    tags=["Profiles"],
    responses=documented_responses(401, 403, 409, 503),
)
async def update_profile(
    _origin: Origin,
    payload: ProfileUpdate,
    profiles: Profiles,
    response: Response,
    current_user: CurrentUser,
) -> OwnProfileResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await queries.own_response(await profiles.update(current_user.id, payload))


@router.patch(
    "/me/badges/{code}",
    response_model=OwnProfileResponse,
    summary="Change your badge visibility",
    description=(
        "Send enabled and your expected profile revision. Requires your own assignment; "
        "unknown codes return 404, disabling a mandatory badge returns 403, and stale "
        "revisions or concurrent writes return 409. Returns your updated own profile and "
        "revision with private, no-store."
    ),
    tags=["Profiles"],
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def update_badge_preferences(
    _origin: Origin,
    code: str,
    payload: BadgePreferenceUpdate,
    profiles: Profiles,
    response: Response,
    current_user: CurrentUser,
) -> OwnProfileResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await queries.own_response(
        await profiles.update(current_user.id, payload, badge_code=code)
    )


@router.get(
    "/users/{username}/followers",
    response_model=list[ProfileUserResponse],
    summary="List followers",
    description=(
        "Returns compact public profile cards. Offset defaults to 0; limit defaults to 20 and "
        "is capped at 100."
    ),
    tags=["Profiles"],
    responses=documented_responses(404, 503),
)
async def list_followers(
    username: Username,
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip; refresh from zero after concurrent list changes.",
    ),
    limit: int = Query(
        default=20, ge=1, le=100, description="Page size from 1 to 100; defaults to 20."
    ),
) -> list[ProfileUserResponse]:
    return await queries.network(username, "followers", offset, limit)


@router.get(
    "/users/{username}/following",
    response_model=list[ProfileUserResponse],
    summary="List followed profiles",
    description=(
        "Returns compact public profile cards. Offset defaults to 0; limit defaults to 20 and "
        "is capped at 100."
    ),
    tags=["Profiles"],
    responses=documented_responses(404, 503),
)
async def list_following(
    username: Username,
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip; refresh from zero after concurrent list changes.",
    ),
    limit: int = Query(
        default=20, ge=1, le=100, description="Page size from 1 to 100; defaults to 20."
    ),
) -> list[ProfileUserResponse]:
    return await queries.network(username, "following", offset, limit)


@router.put(
    "/users/{username}/follow",
    status_code=204,
    summary="Follow a profile",
    description="Idempotently creates a follow relationship; following yourself returns 400.",
    tags=["Profiles"],
    responses=documented_responses(400, 401, 403, 404, 409, 503),
)
async def follow_user(
    _origin: Origin,
    username: Username,
    current_user: CurrentUser,
    profiles: Profiles,
) -> Response:
    await profiles.follow(current_user, username)
    return Response(status_code=204)


@router.delete(
    "/users/{username}/follow",
    status_code=204,
    summary="Unfollow a profile",
    description="Idempotently removes the follow relationship.",
    tags=["Profiles"],
    responses=documented_responses(401, 403, 404, 409, 503),
)
async def unfollow_user(
    _origin: Origin,
    username: Username,
    current_user: CurrentUser,
    profiles: Profiles,
) -> Response:
    await profiles.unfollow(current_user, username)
    return Response(status_code=204)
