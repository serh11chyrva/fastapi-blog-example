from datetime import datetime
import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Credentials and public identity for creating an account."""

    email: EmailStr = Field(examples=["reader@example.com"])
    username: str = Field(min_length=3, max_length=24, examples=["reader_one"])
    display_name: str = Field(min_length=1, max_length=64, examples=["Avery Reader"])
    password: str = Field(min_length=12, max_length=256, examples=["Correct-Horse-Battery-42"])

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        normalized = value.removeprefix("@").lower()
        if not re.fullmatch(r"[a-z0-9_]{3,24}", normalized):
            raise ValueError("Username must use 3-24 letters, numbers, or underscores")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Display name cannot be empty")
        return value


class LoginRequest(BaseModel):
    """An email address or username and its password."""

    identifier: str = Field(min_length=3, max_length=320, examples=["reader@example.com"])
    password: str = Field(min_length=1, max_length=256, examples=["Correct-Horse-Battery-42"])


class SessionResponse(BaseModel):
    """A server-side session; the raw session token is never returned."""

    id: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    ip_address: str | None
    user_agent: str | None
    current: bool


class AuthResponse(BaseModel):
    """Safe public account fields returned after registration or login."""

    id: str
    email: str
    username: str
    display_name: str
