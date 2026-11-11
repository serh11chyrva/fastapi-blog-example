"""HTTP adapters for public profiles and owner settings."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from backend.api.metadata import Origin, Username, documented_responses
from backend.audit.dependencies import Audit
from backend.auth.dependencies import CurrentUser, OptionalUser
from backend.core.resources import Resources
from backend.feeds.repository import FeedKind
from backend.feeds.schemas import FeedItem, ProfileTimelinePage
from backend.links.presentation import hydrate_publications
from backend.profiles.queries import ProfileQueries
from backend.profiles.schemas import (
    BadgePreferenceUpdate,
    OwnProfileResponse,
    ProfileResponse,
    ProfileUpdate,
    ProfileUserResponse,
)
from backend.profiles.service import ProfileService
from backend.profiles.timeline import profile_timeline

router = APIRouter()
queries = ProfileQueries()


def get_profile_service(resources: Resources, audit: Audit) -> ProfileService:
    """Create the profile service from request-scoped dependencies.

    :param resources: Application-owned database, cache, and storage clients.
    :param audit: Request metadata attached to audited operations.
    :return: The configured profile service.
    """
    return ProfileService(resources, audit)


Profiles = Annotated[ProfileService, Depends(get_profile_service)]


@router.get(
    "/users/{username}",
    response_model=ProfileResponse,
    summary="Get a public profile",
    description=("Username is case-insensitive; follow state is relative to the optional current session."),
    tags=["Profiles"],
    responses=documented_responses(404, 503),
    openapi_extra={"security": [{}, {"SessionCookie": []}]},
)
async def get_profile(username: Username, current_user: OptionalUser) -> ProfileResponse:
    """Read a public profile with viewer-specific follow state.

    :param username: Public profile handle, optionally prefixed with @.
    :param current_user: Account resolved from the session cookie, or None for anonymous
        access.
    :return: The public profile response.
    """
    return await queries.response(await queries.by_username(username), current_user.id if current_user else None)


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
    resources: Resources,
    kind: FeedKind = "all",
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip; refresh from zero after concurrent list changes.",
    ),
    limit: int = Query(default=50, ge=1, le=50, description="Page size from 1 to 50; defaults to 50."),
) -> list[FeedItem]:
    """Read an offset page of a profile's public publications.

    Cached link presentations are attached after access checks; missing metadata is queued, not fetched here.

    :param resources: Application cache used to attach current link presentations.
    :param username: Public profile handle, optionally prefixed with @.
    :param kind: Publication type filter: micro_post, article, or all when supported.
    :param offset: Number of matching entries to skip before selecting the page.
    :param limit: Maximum number of entries to return in this page.
    :return: The requested page of publication feed items.
    """
    return await hydrate_publications(
        resources.redis,
        await queries.publications(username, kind, offset, limit),
    )


@router.get(
    "/users/{username}/timeline",
    response_model=ProfileTimelinePage,
    summary="List public profile activity",
    description="Public authored posts, reposts, and live comments on published articles, newest first.",
    tags=["Profiles"],
    responses=documented_responses(404, 422, 503),
)
async def get_profile_timeline(
    username: Username,
    resources: Resources,
    response: Response,
    cursor: Annotated[str | None, Query(max_length=512, description="Opaque cursor from the previous page.")] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="Page size from 1 to 50.")] = 20,
) -> ProfileTimelinePage:
    """Read current public activity for an existing profile.

    Cached link presentations are attached after access checks; missing metadata is queued, not fetched here.

    :param resources: Application cache used to attach current link presentations.
    :param username: Case-insensitive profile handle.
    :param response: Response whose cache policy prevents reuse after visibility changes.
    :param cursor: Optional position from the previous activity page.
    :param limit: Maximum number of activity entries.
    :return: The public activity page and its next cursor.
    """
    response.headers["Cache-Control"] = "no-store"

    return await hydrate_publications(
        resources.redis,
        await profile_timeline(await queries.by_username(username), cursor, limit),
    )


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
async def get_own_profile(current_user: CurrentUser, response: Response) -> OwnProfileResponse:
    """Read the current account's private profile and disable response caching.

    :param current_user: Account resolved from the current session cookie.
    :param response: HTTP response whose headers, cookies, or status may be updated.
    :return: The owner profile including revision and badge preferences.
    """
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
    """Apply a revision-checked profile update for the current account.

    :param _origin: Validated Origin header required by mutating API operations.
    :param payload: Validated request data for the operation.
    :param profiles: Profile application service injected for this request.
    :param response: HTTP response whose headers, cookies, or status may be updated.
    :param current_user: Account resolved from the current session cookie.
    :return: The updated owner profile response.
    """
    response.headers["Cache-Control"] = "private, no-store"

    return await queries.own_response(await profiles.update(current_user.id, payload))


@router.delete(
    "/me/banner", status_code=204, summary="Remove your profile banner",
    description="Detach the banner, advance the profile revision, and queue cleanup. Repeated requests are safe.",
    tags=["Media"], responses=documented_responses(401, 403, 404, 409, 503),
)
async def remove_banner(_origin: Origin, current_user: CurrentUser, profiles: Profiles) -> Response:
    """Detach the authenticated owner's banner.

    :param _origin: Required same-origin mutation header.
    :param current_user: Account whose banner is removed.
    :param profiles: Request-scoped profile service.
    :return: Empty response after the banner is detached.
    """
    await profiles.remove_banner(current_user)

    return Response(status_code=204)


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
    """Update an owned badge's visibility using the current profile revision.

    :param _origin: Validated Origin header required by mutating API operations.
    :param code: Code of the assigned badge to update.
    :param payload: Validated request data for the operation.
    :param profiles: Profile application service injected for this request.
    :param response: HTTP response whose headers, cookies, or status may be updated.
    :param current_user: Account resolved from the current session cookie.
    :return: The updated owner profile response.
    """
    response.headers["Cache-Control"] = "private, no-store"

    return await queries.own_response(await profiles.update(current_user.id, payload, badge_code=code))


@router.get(
    "/users/{username}/followers",
    response_model=list[ProfileUserResponse],
    summary="List followers",
    description=(
        "Returns compact public profile cards. Offset defaults to 0; limit defaults to 20 and is capped at 100."
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
    limit: int = Query(default=20, ge=1, le=100, description="Page size from 1 to 100; defaults to 20."),
) -> list[ProfileUserResponse]:
    """List accounts following the requested profile.

    :param username: Public profile handle, optionally prefixed with @.
    :param offset: Number of matching entries to skip before selecting the page.
    :param limit: Maximum number of entries to return in this page.
    :return: The requested page of public follower cards.
    """
    return await queries.network(username, "followers", offset, limit)


@router.get(
    "/users/{username}/following",
    response_model=list[ProfileUserResponse],
    summary="List followed profiles",
    description=(
        "Returns compact public profile cards. Offset defaults to 0; limit defaults to 20 and is capped at 100."
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
    limit: int = Query(default=20, ge=1, le=100, description="Page size from 1 to 100; defaults to 20."),
) -> list[ProfileUserResponse]:
    """List accounts followed by the requested profile.

    :param username: Public profile handle, optionally prefixed with @.
    :param offset: Number of matching entries to skip before selecting the page.
    :param limit: Maximum number of entries to return in this page.
    :return: The requested page of public followed-account cards.
    """
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
    """Follow another profile using the authenticated account.

    :param _origin: Validated Origin header required by mutating API operations.
    :param username: Public profile handle, optionally prefixed with @.
    :param current_user: Account resolved from the current session cookie.
    :param profiles: Profile application service injected for this request.
    :return: An empty response with status 204.
    """
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
    """Remove a follow relationship for the authenticated account.

    :param _origin: Validated Origin header required by mutating API operations.
    :param username: Public profile handle, optionally prefixed with @.
    :param current_user: Account resolved from the current session cookie.
    :param profiles: Profile application service injected for this request.
    :return: An empty response with status 204.
    """
    await profiles.unfollow(current_user, username)

    return Response(status_code=204)
