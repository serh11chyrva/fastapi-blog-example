from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.core import api_examples as examples


class RegisterRequest(BaseModel):
    """Credentials and public identity for creating an account."""

    model_config = ConfigDict(title="Account registration", json_schema_extra={"examples": [examples.REGISTER]})

    email: EmailStr = Field(description="Unique email address, stored in lowercase.", examples=[examples.ACCOUNT["email"]])
    username: str = Field(min_length=3, max_length=24, description="Unique public handle: 3-24 ASCII letters, digits, or underscores. A leading @ is removed and letters are lowercased.", examples=[examples.ACCOUNT["username"]])
    display_name: str = Field(min_length=1, max_length=64, description="Public name shown beside publications. Surrounding whitespace is trimmed; blank names are rejected.", examples=[examples.ACCOUNT["display_name"]])
    password: str = Field(min_length=12, max_length=256, description="Account password, between 12 and 256 characters. Never returned in responses.", examples=[examples.PASSWORD], json_schema_extra={"format": "password", "writeOnly": True})

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

    model_config = ConfigDict(title="Login credentials", json_schema_extra={"examples": [examples.LOGIN]})

    identifier: str = Field(min_length=3, max_length=320, description="Account email or username, optionally prefixed with @. Matching is case-insensitive.", examples=[examples.ACCOUNT["email"], "@maya_bennett"])
    password: str = Field(min_length=1, max_length=256, description="Password for the selected account.", examples=[examples.PASSWORD], json_schema_extra={"format": "password", "writeOnly": True})


class SessionResponse(BaseModel):
    """A server-side session; the raw session token is never returned."""

    model_config = ConfigDict(title="Active session", json_schema_extra={"examples": [examples.SESSION]})

    id: str = Field(description="Session identifier used to revoke this session; this is not the cookie token.", examples=[examples.SESSION["id"]])
    created_at: datetime = Field(description="UTC time when the session was created.", examples=[examples.SESSION["created_at"]])
    last_seen_at: datetime = Field(description="UTC time of the most recent recorded authenticated activity.", examples=[examples.SESSION["last_seen_at"]])
    expires_at: datetime = Field(description="Absolute UTC expiry. An idle session may expire earlier.", examples=[examples.SESSION["expires_at"]])
    ip_address: str | None = Field(description="IP address of the most recent recorded authenticated request, or null when unavailable.", examples=[examples.SESSION["ip_address"]])
    user_agent: str | None = Field(description="User-Agent of the most recent recorded authenticated request, truncated to 512 characters; null when unavailable.", examples=[examples.SESSION["user_agent"]])
    current: bool = Field(description="Whether this is the session used for the current request.", examples=[True])


class AuthResponse(BaseModel):
    """Account-owner fields returned after registration, login, or session lookup."""

    model_config = ConfigDict(title="Authenticated account", json_schema_extra={"examples": [examples.ACCOUNT]})

    id: str = Field(description="Account identifier: a 24-character MongoDB ObjectId.", examples=[examples.ACCOUNT["id"]])
    email: str = Field(description="Account email address, visible to the account owner.", examples=[examples.ACCOUNT["email"]])
    username: str = Field(description="Normalized public handle without a leading @.", examples=[examples.ACCOUNT["username"]])
    display_name: str = Field(description="Public name shown on profiles and publications.", examples=[examples.ACCOUNT["display_name"]])
