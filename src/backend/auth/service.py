from dataclasses import dataclass
from typing import Literal, Protocol

from beanie import PydanticObjectId

from backend.auth.models import AuthIdentity
from backend.auth.repository import AuthRepository
from backend.auth.security import (
    hash_password_async,
    password_hash_needs_rehash,
    verify_password_async,
)
from backend.profiles.models import User


class PasswordRepository(Protocol):
    async def find_user_by_identifier(self, identifier: str) -> User | None: ...

    async def find_password_identity(
        self, user_id: PydanticObjectId
    ) -> AuthIdentity | None: ...


@dataclass(frozen=True, slots=True)
class PasswordAuthenticated:
    user: User
    identity: AuthIdentity
    needs_rehash: bool = False
    authenticated: Literal[True] = True


@dataclass(frozen=True, slots=True)
class PasswordRejected:
    user: User | None = None
    identity: AuthIdentity | None = None
    authenticated: Literal[False] = False
    needs_rehash: Literal[False] = False


type PasswordAuthentication = PasswordAuthenticated | PasswordRejected


class AuthService:
    def __init__(self, repository: PasswordRepository = AuthRepository()) -> None:
        self.repository = repository

    async def authenticate_password(
        self, identifier: str, password: str
    ) -> PasswordAuthentication:
        """Authenticate credentials and prepare an optional password hash upgrade.

        When needs_rehash is true, the returned identity contains the new hash.
        The caller persists it within the successful session-creation transaction.
        """
        user = await self.repository.find_user_by_identifier(identifier)
        if user is None:
            return PasswordRejected()
        identity = await self.repository.find_password_identity(user.id)
        if identity is None or identity.password_hash is None:
            return PasswordRejected(user, identity)
        authenticated = await verify_password_async(password, identity.password_hash)
        if not authenticated:
            return PasswordRejected(user, identity)
        needs_rehash = authenticated and password_hash_needs_rehash(
            identity.password_hash
        )
        if needs_rehash:
            identity.password_hash = await hash_password_async(password)
        return PasswordAuthenticated(user, identity, needs_rehash)
