from beanie import PydanticObjectId

from backend.auth.models import AuthIdentity
from backend.profiles.models import User


class AuthRepository:
    """Beanie lookups for accounts and their password identities."""

    @staticmethod
    async def find_user_by_identifier(identifier: str) -> User | None:
        """Find an account by normalized email or public username.

        :param identifier: Account email or public username, optionally prefixed with @.
        :return: The matching user, or None when no account matches.
        """
        normalized = identifier.strip().lower().removeprefix("@")

        if identifier.strip().startswith("@") or "@" not in normalized:
            return await User.find_one(User.username == normalized)

        return await User.find_one(User.email == normalized)

    @staticmethod
    async def find_password_identity(user_id: PydanticObjectId) -> AuthIdentity | None:
        """Find the password identity associated with an account.

        :param user_id: MongoDB identifier of the user account.
        :return: The password identity, or None when none exists.
        """
        return await AuthIdentity.find_one(AuthIdentity.user_id == user_id, AuthIdentity.provider == "password")
