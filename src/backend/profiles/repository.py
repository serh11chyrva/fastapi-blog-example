from typing import Literal

from beanie import PydanticObjectId

from backend.profiles.models import BadgeDefinition, Follow, User


class ProfileRepository:
    """Beanie account, badge catalog, and follow relationship queries."""

    @staticmethod
    async def get_by_id(user_id: PydanticObjectId) -> User | None:
        """Load a user account by its document identifier.

        :param user_id: MongoDB identifier of the user account.
        :return: The matching user, or None when absent.
        """
        return await User.get(user_id)

    @staticmethod
    async def find_by_username(username: str) -> User | None:
        """Find an account by its case-insensitive public handle.

        :param username: Public profile handle, optionally prefixed with @.
        :return: The matching user, or None when absent.
        """
        return await User.find_one(User.username == username.removeprefix("@").lower())

    @staticmethod
    async def counts(user_id: PydanticObjectId) -> tuple[int, int]:
        """Count a user's incoming and outgoing follow relationships.

        :param user_id: MongoDB identifier of the user account.
        :return: The follower count and following count.
        """
        followers = await Follow.find(Follow.followee_id == user_id).count()
        following = await Follow.find(Follow.follower_id == user_id).count()

        return followers, following

    @staticmethod
    async def is_following(follower_id: PydanticObjectId | None, followee_id: PydanticObjectId) -> bool:
        """Check whether one account follows another.

        :param follower_id: Account ID on the follower side, or None for an anonymous
            viewer.
        :param followee_id: Account ID on the followed side of the relationship.
        :return: True when the relationship exists; otherwise False.
        """
        if follower_id is None:
            return False

        return bool(await Follow.find_one(Follow.follower_id == follower_id, Follow.followee_id == followee_id))

    @staticmethod
    async def users_by_ids(user_ids: list[PydanticObjectId]) -> list[User]:
        """Load user accounts for a batch of document identifiers.

        :param user_ids: Batch of user document identifiers to load.
        :return: The matching user documents.
        """
        return await User.find({"_id": {"$in": user_ids}}).to_list() if user_ids else []

    @staticmethod
    async def badge_definitions(codes: list[str]) -> dict[str, BadgeDefinition]:
        """Load shared badge definitions for the supplied codes.

        :param codes: Codes identifying the shared badge definitions to load.
        :return: The matching definitions indexed by badge code.
        """
        definitions = await BadgeDefinition.find({"code": {"$in": codes}}).to_list() if codes else []

        return {definition.code: definition for definition in definitions}

    @staticmethod
    async def connections(
        user_id: PydanticObjectId,
        kind: Literal["followers", "following"],
        offset: int,
        limit: int,
    ) -> list[User]:
        """Load accounts on one side of a user's follow relationships.

        :param user_id: MongoDB identifier of the user account.
        :param kind: Relationship direction: followers or following.
        :param offset: Number of matching entries to skip before selecting the page.
        :param limit: Maximum number of entries to return in this page.
        :return: The requested page of connected user accounts.
        """
        field = "followee_id" if kind == "followers" else "follower_id"
        follows = (
            await Follow.find({field: user_id})
            .sort(("created_at", -1), ("_id", -1))
            .skip(offset)
            .limit(limit)
            .to_list()
        )
        ids = [item.follower_id if kind == "followers" else item.followee_id for item in follows]
        by_id = {user.id: user for user in await ProfileRepository.users_by_ids(ids)}

        return [by_id[user_id] for user_id in ids if user_id in by_id]
