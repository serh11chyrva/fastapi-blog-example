import asyncio
import base64
import hashlib
import hmac
import secrets
from concurrent.futures import ThreadPoolExecutor
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

SCRYPT_N: Final[int] = 1 << 14
SCRYPT_R: Final[int] = 8
SCRYPT_P: Final[int] = 1
PASSWORD_HASHER: Final[PasswordHasher] = PasswordHasher(
    time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16
)
PASSWORD_EXECUTOR: Final[ThreadPoolExecutor] = ThreadPoolExecutor(max_workers=4, thread_name_prefix="password")


async def hash_password_async(password: str) -> str:
    """Hash in a dedicated pool with at most four concurrent password operations.

    :param password: Plaintext password supplied for hashing or authentication.
    :return: The salted, encoded Argon2id password hash.
    """
    return await asyncio.get_running_loop().run_in_executor(PASSWORD_EXECUTOR, hash_password, password)


async def verify_password_async(password: str, encoded: str) -> bool:
    """Keep expensive verification off the event loop, including legacy scrypt.

    :param password: Plaintext password supplied for hashing or authentication.
    :param encoded: Encoded stored password hash, including its algorithm parameters.
    :return: True when the password matches; otherwise False.
    """
    return await asyncio.get_running_loop().run_in_executor(PASSWORD_EXECUTOR, verify_password, password, encoded)


def hash_password(password: str) -> str:
    """Hash a password using the configured Argon2id parameters.

    :param password: Plaintext password supplied for hashing or authentication.
    :return: The salted, encoded password hash.
    """
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    """Verify a password against an Argon2id or legacy scrypt hash.

    :param password: Plaintext password supplied for hashing or authentication.
    :param encoded: Encoded stored password hash, including its algorithm parameters.
    :return: True when the password matches; otherwise False.
    """
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
    """Determine whether a stored password hash needs upgrading.

    :param encoded: Encoded stored password hash, including its algorithm parameters.
    :return: True for legacy hashes or outdated Argon2id parameters.
    """
    if not encoded.startswith("$argon2"):
        return True

    try:
        return PASSWORD_HASHER.check_needs_rehash(encoded)
    except (VerificationError, InvalidHashError):
        return True


def new_session_token() -> str:
    """Generate a cryptographically random opaque session token.

    :return: The plaintext token to deliver to the client.
    """
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Hash a plaintext session token before database lookup or storage.

    :param token: Plaintext session token supplied by the client.
    :return: The hexadecimal SHA-256 token digest.
    """
    return hashlib.sha256(token.encode()).hexdigest()
