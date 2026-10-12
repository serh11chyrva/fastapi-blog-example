from datetime import datetime
import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=24)
    display_name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=12, max_length=256)

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
    identifier: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class SessionResponse(BaseModel):
    id: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    ip_address: str | None
    user_agent: str | None
    current: bool


class AuthResponse(BaseModel):
    id: str
    email: str
    username: str
    display_name: str
