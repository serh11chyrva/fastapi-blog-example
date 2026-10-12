import base64
import hashlib

from backend.core.security import hash_password, hash_session_token, new_session_token, password_hash_needs_rehash, verify_password


def test_password_hash_is_salted_and_verified() -> None:
    first_hash = hash_password("example-long-password")
    second_hash = hash_password("example-long-password")

    assert first_hash != second_hash
    assert verify_password("example-long-password", first_hash)
    assert not verify_password("wrong-password", first_hash)
    assert first_hash.startswith("$argon2id$")


def test_legacy_scrypt_hashes_remain_verifiable_and_are_marked_for_upgrade() -> None:
    salt = b"legacy-salt-for-tests"
    digest = hashlib.scrypt(b"example-long-password", salt=salt, n=1 << 14, r=8, p=1)
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

    assert verify_password("example-long-password", legacy_hash)
    assert not verify_password("wrong-password", legacy_hash)
    assert password_hash_needs_rehash(legacy_hash)


def test_session_token_is_random_and_only_its_hash_is_persisted() -> None:
    token = new_session_token()

    assert len(token) >= 40
    assert hash_session_token(token) != token
    assert hash_session_token(token) == hash_session_token(token)
