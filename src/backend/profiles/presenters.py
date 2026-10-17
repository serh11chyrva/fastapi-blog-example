"""Pure profile response construction, keeping owner-only data explicit."""

from backend.links.models import ProfileLink
from backend.links.platforms import detect_platform
from backend.profiles.models import BadgeDefinition, User
from backend.profiles.schemas import (
    AvatarResponse,
    BadgeResponse,
    LinkResponse,
    OwnerBadgeResponse,
    OwnProfileResponse,
    ProfileResponse,
    ProfileUserResponse,
)


def avatars(user: User) -> AvatarResponse:
    """Present available variants of a user's optional avatar.

    :param user: User account used by the operation.
    :return: Avatar variants with a relative original URL, or a null original when absent.
    """
    image = user.avatars.original
    original = f"/static/images/avatars/{image.key.rsplit('/', 1)[-1]}" if image else None

    return AvatarResponse(original=original)


def link_response(link: ProfileLink) -> LinkResponse:
    """Present a saved link with its detected platform and redirect URL.

    :param link: Saved profile link to present.
    :return: The versioned public link response.
    """
    return LinkResponse(
        **link.model_dump(),
        platform=detect_platform(link.url),
        redirect_url=f"/api/v1/links/{link.id}/redirect",
    )


def user_card(user: User) -> ProfileUserResponse:
    """Present an account as a compact public profile card.

    :param user: User account used by the operation.
    :return: The public user card without private account fields.
    """
    return ProfileUserResponse(
        id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        avatars=avatars(user),
    )


def public_profile(
    user: User,
    definitions: dict[str, BadgeDefinition],
    follower_count: int,
    following_count: int,
    is_following: bool,
) -> ProfileResponse:
    """Assemble public profile fields and visible badge assignments.

    :param user: User account used by the operation.
    :param definitions: Shared badge definitions indexed by badge code.
    :param follower_count: Number of accounts following the profile.
    :param following_count: Number of accounts followed by the profile.
    :param is_following: Whether the current viewer follows this profile.
    :return: The public profile with follow counts and viewer relationship.
    """
    return ProfileResponse(
        id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        bio=user.bio,
        links=[link_response(link) for link in user.links],
        avatars=avatars(user),
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
    """Extend a public profile with revision and private badge preferences.

    :param user: User account used by the operation.
    :param public: Already assembled public portion of the owner profile.
    :param definitions: Shared badge definitions indexed by badge code.
    :return: The owner's profile response.
    """
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
