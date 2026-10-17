from beanie import PydanticObjectId

from backend.auth.models import AuthIdentity
from backend.profiles.models import User


class AuthRepository:
    @staticmethod
    async def find_user_by_identifier(identifier: str) -> User | None:
        normalized = identifier.strip().lower().removeprefix("@")
        if identifier.strip().startswith("@") or "@" not in normalized:
            return await User.find_one(User.username == normalized)
        return await User.find_one(User.email == normalized)

    @staticmethod
    async def find_password_identity(user_id: PydanticObjectId) -> AuthIdentity | None:
        return await AuthIdentity.find_one(
            AuthIdentity.user_id == user_id, AuthIdentity.provider == "password"
        )
