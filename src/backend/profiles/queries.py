"""Read operations assembling profile data before pure response construction."""

from typing import Literal

from beanie import PydanticObjectId

from backend.core.errors import NotFound, Unavailable
from backend.feeds.presenters import feed_item
from backend.feeds.repository import FeedKind, FeedRepository
from backend.feeds.schemas import FeedItem
from backend.posts.models import MicroPost
from backend.posts.visibility import visible_post_stages
from backend.profiles.models import BadgeDefinition, User
from backend.profiles.presenters import own_profile, public_profile, user_card
from backend.profiles.repository import ProfileRepository
from backend.profiles.schemas import OwnProfileResponse, ProfileResponse, ProfileUserResponse


class ProfileQueries:
    """Read operations assembling public and owner-specific profile responses."""

    def __init__(self, repository: ProfileRepository | None = None) -> None:
        """Initialize profile reads with an optional repository override.

        :param repository: Persistence collaborator used to load domain records.
        :return: None.
        """
        self.repository = repository or ProfileRepository()

    async def by_username(self, username: str) -> User:
        """Resolve a public username or raise a profile not-found error.

        :param username: Public profile handle, optionally prefixed with @.
        :return: The matching user account.
        """
        user = await self.repository.find_by_username(username)

        if user is None:
            raise NotFound("Profile not found")

        return user

    async def definitions(self, user: User) -> dict[str, BadgeDefinition]:
        """Load all badge definitions required by a user's assignments.

        :param user: User account used by the operation.
        :return: Badge definitions indexed by code.
        """
        definitions = await self.repository.badge_definitions([badge.code for badge in user.badges])

        if any(badge.code not in definitions for badge in user.badges):
            raise Unavailable("Badge definition is unavailable")

        return definitions

    async def response(self, user: User, viewer_id: PydanticObjectId | None) -> ProfileResponse:
        """Load badge and relationship data for a public profile response.

        :param user: User account used by the operation.
        :param viewer_id: Current viewer account ID, or None for anonymous access.
        :return: The profile as visible to the supplied viewer.
        """
        return await self._response(user, viewer_id, await self.definitions(user))

    async def _response(
        self, user: User, viewer_id: PydanticObjectId | None, definitions: dict[str, BadgeDefinition],
    ) -> ProfileResponse:
        """Load the public profile counters and apply the supplied badge definitions.

        :param user: Public profile account.
        :param viewer_id: Current viewer ID, or None for anonymous reads.
        :param definitions: Badge definitions already resolved for the profile.
        :return: Public profile and viewer-specific follow state.
        """
        followers, following = await self.repository.counts(user.id)

        return public_profile(
            user,
            definitions,
            followers,
            following,
            await self.repository.is_following(viewer_id, user.id),
            sum(row["count"] for row in await MicroPost.aggregate([
                {"$match": {"deleted_at": None, "$or": [{"owner_id": user.id}, {"featured_author_ids": user.id}]}},
                *visible_post_stages(), {"$count": "count"},
            ]).to_list()),
        )

    async def own_response(self, user: User) -> OwnProfileResponse:
        """Assemble a profile including owner-only badge preferences.

        :param user: User account used by the operation.
        :return: The private owner profile response.
        """
        definitions = await self.definitions(user)
        public = await self._response(user, user.id, definitions)

        return own_profile(user, public, definitions)

    async def own_by_id(self, user_id: PydanticObjectId) -> OwnProfileResponse:
        """Load an account and assemble its private profile response.

        :param user_id: MongoDB identifier of the user account.
        :return: The owner profile for the supplied account ID.
        """
        user = await self.repository.get_by_id(user_id)

        if user is None:
            raise NotFound("Profile not found")

        return await self.own_response(user)

    async def publications(self, username: str, kind: FeedKind, offset: int, limit: int) -> list[FeedItem]:
        """Load a page of public publications for a profile.

        :param username: Public profile handle, optionally prefixed with @.
        :param kind: Publication type filter: micro_post, article, or all when
            supported.
        :param offset: Number of matching entries to skip before selecting the page.
        :param limit: Maximum number of entries to return in this page.
        :return: The profile's feed items ordered newest first.
        """
        user = await self.by_username(username)
        entries = await FeedRepository.list_publications(user.id, kind, offset=offset, limit=limit)

        ids = list({author_id for entry in entries for author_id in entry.publication.author_ids})
        by_id = {author.id: author for author in await self.repository.users_by_ids(ids)}

        return [
            feed_item(entry.publication, [by_id[author_id] for author_id in entry.publication.author_ids])
            for entry in entries
            if all(author_id in by_id for author_id in entry.publication.author_ids)
        ]

    async def network(
        self,
        username: str,
        kind: Literal["followers", "following"],
        offset: int,
        limit: int,
    ) -> list[ProfileUserResponse]:
        """Load a page of a profile's followers or followed accounts.

        :param username: Public profile handle, optionally prefixed with @.
        :param kind: Relationship direction: followers or following.
        :param offset: Number of matching entries to skip before selecting the page.
        :param limit: Maximum number of entries to return in this page.
        :return: The requested page of public user cards.
        """
        user = await self.by_username(username)

        return [user_card(item) for item in await self.repository.connections(user.id, kind, offset, limit)]
