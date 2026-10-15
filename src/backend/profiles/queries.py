"""Read operations assembling profile data before pure response construction."""

from typing import Literal

from beanie import PydanticObjectId

from backend.content.presenters import feed_item
from backend.content.repository import ContentRepository, FeedKind
from backend.content.schemas import FeedItem
from backend.core.errors import NotFound, Unavailable
from backend.profiles.models import BadgeDefinition, User
from backend.profiles.presenters import own_profile, public_profile, user_card
from backend.profiles.repository import ProfileRepository
from backend.profiles.schemas import OwnProfileResponse, ProfileResponse, ProfileUserResponse


class ProfileQueries:
    def __init__(self, repository: ProfileRepository | None = None) -> None:
        self.repository = repository or ProfileRepository()

    async def by_username(self, username: str) -> User:
        user = await self.repository.find_by_username(username)
        if user is None:
            raise NotFound("Profile not found")
        return user

    async def definitions(self, user: User) -> dict[str, BadgeDefinition]:
        definitions = await self.repository.badge_definitions([badge.code for badge in user.badges])
        if any(badge.code not in definitions for badge in user.badges):
            raise Unavailable("Badge definition is unavailable")
        return definitions

    async def response(self, user: User, viewer_id: PydanticObjectId | None) -> ProfileResponse:
        definitions = await self.definitions(user)
        followers, following = await self.repository.counts(user.id)
        return public_profile(user, definitions, followers, following, await self.repository.is_following(viewer_id, user.id))

    async def own_response(self, user: User) -> OwnProfileResponse:
        definitions = await self.definitions(user)
        followers, following = await self.repository.counts(user.id)
        public = public_profile(user, definitions, followers, following, await self.repository.is_following(user.id, user.id))
        return own_profile(user, public, definitions)


    async def own_by_id(self, user_id: PydanticObjectId) -> OwnProfileResponse:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise NotFound("Profile not found")
        return await self.own_response(user)


    async def publications(self, username: str, kind: FeedKind, offset: int, limit: int) -> list[FeedItem]:
        user = await self.by_username(username)
        entries = await ContentRepository.list_publications(user.id, kind, offset=offset, limit=limit)
        return [feed_item(entry.publication, user) for entry in entries]

    async def network(
        self,
        username: str,
        kind: Literal["followers", "following"],
        offset: int,
        limit: int,
    ) -> list[ProfileUserResponse]:
        user = await self.by_username(username)
        return [user_card(item) for item in await self.repository.connections(user.id, kind, offset, limit)]
