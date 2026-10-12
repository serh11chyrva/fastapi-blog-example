from beanie import PydanticObjectId

from backend.profiles.models import Follow, User


class ProfileRepository:
    @staticmethod
    async def get_by_id(user_id: PydanticObjectId) -> User | None:
        return await User.get(user_id)

    @staticmethod
    async def find_by_username(username: str) -> User | None:
        return await User.find_one(User.username == username.removeprefix("@").lower())

    @staticmethod
    async def counts(user_id: PydanticObjectId) -> tuple[int, int]:
        followers = await Follow.find(Follow.followee_id == user_id).count()
        following = await Follow.find(Follow.follower_id == user_id).count()
        return followers, following

    @staticmethod
    async def is_following(follower_id: PydanticObjectId | None, followee_id: PydanticObjectId) -> bool:
        if follower_id is None:
            return False
        return bool(await Follow.find_one(Follow.follower_id == follower_id, Follow.followee_id == followee_id))

    @staticmethod
    async def users_by_ids(user_ids: list[PydanticObjectId]) -> list[User]:
        return await User.find({"_id": {"$in": user_ids}}).to_list() if user_ids else []
