import base64
import hashlib
import hmac
import secrets
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


SCRYPT_N: Final[int] = 1 << 14
SCRYPT_R: Final[int] = 8
SCRYPT_P: Final[int] = 1
PASSWORD_HASHER: Final[PasswordHasher] = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16)


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    if encoded.startswith("$argon2"):
        try:
            return PASSWORD_HASHER.verify(encoded, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    # Keep old demo accounts usable and upgrade their hashes after successful login.
    try:
        algorithm, n, r, p, salt_text, digest_text = encoded.split("$", maxsplit=5)
        if algorithm != "scrypt" or int(n) > 1 << 18:
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, OverflowError):
        return False


def password_hash_needs_rehash(encoded: str) -> bool:
    if not encoded.startswith("$argon2"):
        return True
    try:
        return PASSWORD_HASHER.check_needs_rehash(encoded)
    except (VerificationError, InvalidHashError):
        return True


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
