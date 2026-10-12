from dataclasses import dataclass

from backend.auth.models import AuthIdentity
from backend.auth.repository import AuthRepository
from backend.core.security import hash_password, password_hash_needs_rehash, verify_password
from backend.profiles.models import User


@dataclass
class PasswordAuthentication:
    user: User | None
    identity: AuthIdentity | None
    authenticated: bool
    needs_rehash: bool = False


class AuthService:
    def __init__(self, repository: type[AuthRepository] = AuthRepository) -> None:
        self.repository = repository

    async def authenticate_password(self, identifier: str, password: str) -> PasswordAuthentication:
        user = await self.repository.find_user_by_identifier(identifier)
        if user is None:
            return PasswordAuthentication(None, None, False)
        identity = await self.repository.find_password_identity(user.id)
        if identity is None or identity.password_hash is None:
            return PasswordAuthentication(user, identity, False)
        authenticated = verify_password(password, identity.password_hash)
        needs_rehash = authenticated and password_hash_needs_rehash(identity.password_hash)
        if needs_rehash:
            identity.password_hash = hash_password(password)
        return PasswordAuthentication(
            user,
            identity,
            authenticated,
            needs_rehash,
        )
