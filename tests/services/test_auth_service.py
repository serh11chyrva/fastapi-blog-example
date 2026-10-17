import base64
import hashlib
from types import SimpleNamespace

import pytest

from backend.auth.service import AuthService
from backend.core.security import verify_password


@pytest.mark.asyncio
async def test_auth_service_upgrades_legacy_password_after_successful_authentication() -> (
    None
):
    user = SimpleNamespace(id="user-id")
    salt = b"legacy-salt-for-service"
    digest = hashlib.scrypt(b"correct-password", salt=salt, n=1 << 14, r=8, p=1)
    legacy_hash = "$".join(
        (
            "scrypt",
            str(1 << 14),
            "8",
            "1",
            base64.urlsafe_b64encode(salt).decode(),
            base64.urlsafe_b64encode(digest).decode(),
        )
    )
    identity = SimpleNamespace(user_id=user.id, password_hash=legacy_hash)

    class MemoryAuthRepository:
        @staticmethod
        async def find_user_by_identifier(identifier: str):
            assert identifier == "writer@example.com"
            return user

        @staticmethod
        async def find_password_identity(user_id: str):
            assert user_id == user.id
            return identity

    result = await AuthService(MemoryAuthRepository).authenticate_password(
        "writer@example.com", "correct-password"
    )

    assert result.authenticated
    assert result.user is user
    assert result.needs_rehash
    assert identity.password_hash != legacy_hash
    assert verify_password("correct-password", identity.password_hash)


@pytest.mark.asyncio
async def test_auth_service_rejects_an_incorrect_password() -> None:
    user = SimpleNamespace(id="user-id")
    identity = SimpleNamespace(user_id=user.id, password_hash="$unsupported$hash")

    class MemoryAuthRepository:
        @staticmethod
        async def find_user_by_identifier(identifier: str):
            return user

        @staticmethod
        async def find_password_identity(user_id: str):
            return identity

    result = await AuthService(MemoryAuthRepository).authenticate_password(
        "writer@example.com", "incorrect-password"
    )

    assert not result.authenticated
    assert not result.needs_rehash
