from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.auth.client import ClientType
from backend.api import examples


class SessionClientRequest(BaseModel):
    """Display metadata supplied when creating a session; never used for authorization."""

    client_type: ClientType = Field(default=ClientType.WEB, description="Client creating this session: web, mobile, or desktop. Fixed for the session lifetime.")
    device_name: str | None = Field(default=None, min_length=1, max_length=128, description="Optional device label for mobile or desktop apps, such as iPhone 16 or Work laptop. Ignored for web, which uses the parsed browser and OS.", examples=["iPhone 16"])

    @field_validator("device_name")
    @classmethod
    def normalize_device_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value or any(not character.isprintable() for character in value):
            raise ValueError("Device name must contain printable characters and cannot be blank")
        return value


class RegisterRequest(SessionClientRequest):
    """Credentials and public identity for creating an account."""

    model_config = ConfigDict(title="Account registration", json_schema_extra={"examples": [examples.REGISTER]})

    email: EmailStr = Field(description="Unique email address, stored in lowercase.", examples=[examples.ACCOUNT["email"]])
    username: str = Field(min_length=3, max_length=25, pattern=r"^@?[a-zA-Z0-9_]{3,24}$", description="Unique public handle: 3-24 ASCII letters, digits, or underscores. A leading @ is removed and letters are lowercased.", examples=[examples.ACCOUNT["username"]])
    display_name: str = Field(min_length=1, max_length=64, description="Public name shown beside publications. Surrounding whitespace is trimmed; blank names are rejected.", examples=[examples.ACCOUNT["display_name"]])
    password: str = Field(min_length=12, max_length=256, description="Account password, between 12 and 256 characters. Never returned in responses.", examples=[examples.PASSWORD], json_schema_extra={"format": "password", "writeOnly": True})

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Username must be a string")
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


class LoginRequest(SessionClientRequest):
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
    client_type: ClientType = Field(description="Client category saved at registration or login. Older sessions default to web.", examples=["web"])
    location: str = Field(description="Approximate location of the latest recorded IP, formatted as city, region, country in English, omitting missing or duplicate parts. Unknown location when unavailable. Raw IP addresses are never returned.", examples=[examples.SESSION["location"]])
    device: str = Field(description="Browser and OS for web; supplied device label with parsed OS, or parsed device/OS for mobile and desktop. Unknown browser/device when unavailable. Raw User-Agent is never returned.", examples=[examples.SESSION["device"]])
    current: bool = Field(description="Whether this is the session used for the current request.", examples=[True])


class AuthResponse(BaseModel):
    """Account-owner fields returned after registration, login, or session lookup."""

    model_config = ConfigDict(title="Authenticated account", json_schema_extra={"examples": [examples.ACCOUNT]})

    id: str = Field(description="Account identifier: a 24-character MongoDB ObjectId.", examples=[examples.ACCOUNT["id"]])
    email: str = Field(description="Account email address, visible to the account owner.", examples=[examples.ACCOUNT["email"]])
    username: str = Field(description="Normalized public handle without a leading @.", examples=[examples.ACCOUNT["username"]])
    display_name: str = Field(description="Public name shown on profiles and publications.", examples=[examples.ACCOUNT["display_name"]])
