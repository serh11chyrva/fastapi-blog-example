from beanie import PydanticObjectId

from backend.profiles.links import detect_platform, validate_link_url
from backend.profiles.models import ProfileLink, User
from backend.profiles.repository import ProfileRepository
from backend.profiles.schemas import BadgeResponse, LinkResponse, ProfileResponse, ProfileUserResponse


class ProfileService:
    def __init__(self, repository: type[ProfileRepository] = ProfileRepository) -> None:
        self.repository = repository

    @staticmethod
    def avatar_url(user: User) -> str | None:
        if not user.avatar_key:
            return None
        return f"/static/images/avatars/{user.avatar_key.rsplit('/', 1)[-1]}"

    async def response(self, user: User, viewer_id: PydanticObjectId | None) -> ProfileResponse:
        follower_count, following_count = await self.repository.counts(user.id)
        return ProfileResponse(
            id=str(user.id),
            username=user.username,
            display_name=user.display_name,
            bio=user.bio,
            links=[self.link_response(user, link) for link in user.links],
            avatar_url=self.avatar_url(user),
            badges=[BadgeResponse(**badge.model_dump()) for badge in user.badges],
            follower_count=follower_count,
            following_count=following_count,
            is_following=await self.repository.is_following(viewer_id, user.id),
        )

    @staticmethod
    def link_response(user: User, link: ProfileLink) -> LinkResponse:
        return LinkResponse(
            **link.model_dump(),
            platform=detect_platform(link.url),
            redirect_url=f"/api/v1/users/{user.username}/links/{link.id}/redirect",
        )

    @staticmethod
    def redirect_destination(link: ProfileLink) -> str:
        """Resolve a saved target; future attribution and click analytics belong here."""
        return validate_link_url(link.url)

    def user_card(self, user: User) -> ProfileUserResponse:
        return ProfileUserResponse(
            id=str(user.id),
            username=user.username,
            display_name=user.display_name,
            avatar_url=self.avatar_url(user),
        )
