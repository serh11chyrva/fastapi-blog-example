"""Pure profile response construction, keeping owner-only data explicit."""

from backend.links.models import ProfileLink
from backend.links.platforms import detect_platform
from backend.profiles.models import BadgeDefinition, User
from backend.profiles.schemas import (
    BadgeResponse,
    LinkResponse,
    OwnerBadgeResponse,
    OwnProfileResponse,
    ProfileResponse,
    ProfileUserResponse,
)


def avatar_url(user: User) -> str | None:
    return (
        f"/static/images/avatars/{user.avatar_key.rsplit('/', 1)[-1]}"
        if user.avatar_key
        else None
    )


def link_response(link: ProfileLink) -> LinkResponse:
    return LinkResponse(
        **link.model_dump(),
        platform=detect_platform(link.url),
        redirect_url=f"/api/v1/links/{link.id}/redirect",
    )


def user_card(user: User) -> ProfileUserResponse:
    return ProfileUserResponse(
        id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        avatar_url=avatar_url(user),
    )


def public_profile(
    user: User,
    definitions: dict[str, BadgeDefinition],
    follower_count: int,
    following_count: int,
    is_following: bool,
) -> ProfileResponse:
    return ProfileResponse(
        id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        bio=user.bio,
        links=[link_response(link) for link in user.links],
        avatar_url=avatar_url(user),
        badges=[
            BadgeResponse(
                version=definitions[badge.code].version,
                code=badge.code,
                payload=definitions[badge.code].payload,
            )
            for badge in user.badges
            if badge.enabled
        ],
        follower_count=follower_count,
        following_count=following_count,
        is_following=is_following,
    )


def own_profile(
    user: User,
    public: ProfileResponse,
    definitions: dict[str, BadgeDefinition],
) -> OwnProfileResponse:
    return OwnProfileResponse(
        **public.model_dump(exclude={"badges"}),
        revision=user.revision,
        badges=[
            OwnerBadgeResponse(
                version=definitions[badge.code].version,
                code=badge.code,
                payload=definitions[badge.code].payload,
                assigned_at=badge.assigned_at,
                preferences={"enabled": badge.enabled},
                permissions={"can_disable": definitions[badge.code].can_disable},
            )
            for badge in user.badges
        ],
    )
