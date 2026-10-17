"""Compatibility exports for callers using the original security module."""

from backend.auth.security import (
    hash_password,
    hash_password_async,
    hash_session_token,
    new_session_token,
    password_hash_needs_rehash,
    verify_password,
    verify_password_async,
)

__all__ = [
    "hash_password",
    "hash_password_async",
    "hash_session_token",
    "new_session_token",
    "password_hash_needs_rehash",
    "verify_password",
    "verify_password_async",
]
