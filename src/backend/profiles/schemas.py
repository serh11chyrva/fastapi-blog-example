from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.core import api_examples as examples


class LinkInput(BaseModel):
    """A public profile link. Only HTTP and HTTPS URLs are accepted."""

    model_config = ConfigDict(title="Profile link", json_schema_extra={"examples": [examples.LINK]})

    label: str = Field(min_length=1, max_length=32, description="Short public label for the link.", examples=[examples.LINK["label"]])
    url: str = Field(min_length=8, max_length=500, description="Absolute HTTP or HTTPS URL with a hostname.", examples=[examples.LINK["url"]])

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError("Links must use an http or https URL")
        return value


class ProfileUpdate(BaseModel):
    """Partial profile update. Omitted fields are left unchanged."""

    model_config = ConfigDict(title="Profile changes", json_schema_extra={"examples": [examples.PROFILE_UPDATE]})

    display_name: str | None = Field(default=None, min_length=1, max_length=64, description="Replacement public name, trimmed and nonblank. Omit or use null to keep the current value.", examples=[examples.ACCOUNT["display_name"]])
    bio: str | None = Field(default=None, max_length=280, description="Replacement biography. Use an empty string to clear it; omit or use null to leave it unchanged.", examples=[examples.PROFILE_UPDATE["bio"]])
    links: list[LinkInput] | None = Field(default=None, max_length=8, description="Replacement list of up to eight public links. Use [] to clear links; omit or use null to keep them.", examples=[[examples.LINK]])

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Display name cannot be empty")
        return value


class BadgeResponse(BaseModel):
    """A badge assigned to a profile in the demo."""

    model_config = ConfigDict(title="Profile badge", json_schema_extra={"examples": [examples.BADGE]})

    code: str = Field(description="Machine-readable badge code.", examples=[examples.BADGE["code"]])
    label: str = Field(description="Public badge name.", examples=[examples.BADGE["label"]])
    description: str | None = Field(description="Explanation of the badge, or null when absent.", examples=[examples.BADGE["description"]])
    assigned_at: datetime = Field(description="UTC time when the badge was assigned.", examples=[examples.BADGE["assigned_at"]])


class ProfileResponse(BaseModel):
    """A public profile, with follow state relative to the requesting viewer."""

    model_config = ConfigDict(title="Public profile", json_schema_extra={"examples": [examples.PROFILE]})

    id: str = Field(description="Account identifier: a 24-character MongoDB ObjectId.", examples=[examples.ACCOUNT["id"]])
    username: str = Field(description="Normalized public handle without a leading @.", examples=[examples.ACCOUNT["username"]])
    display_name: str = Field(description="Public name displayed on the profile.", examples=[examples.ACCOUNT["display_name"]])
    bio: str = Field(description="Public biography; an empty string means none was provided.", examples=[examples.PROFILE["bio"]])
    links: list[LinkInput] = Field(description="Public links in the order chosen by the profile owner.", examples=[[examples.LINK]])
    avatar_url: str | None = Field(description="Same-origin avatar URL, or null when no avatar is set.", examples=[examples.AVATAR_URL])
    badges: list[BadgeResponse] = Field(description="Badges assigned to the profile; empty when none are assigned.", examples=[[examples.BADGE]])
    follower_count: int = Field(description="Number of accounts following this profile.", examples=[127])
    following_count: int = Field(description="Number of accounts this profile follows.", examples=[43])
    is_following: bool = Field(description="Whether the current viewer follows this profile; false for anonymous viewers.", examples=[False])


class ProfileUserResponse(BaseModel):
    """Compact profile card used by follower and following lists."""

    model_config = ConfigDict(title="Public profile card", json_schema_extra={"examples": [examples.PROFILE_USER]})

    id: str = Field(description="Account identifier: a 24-character MongoDB ObjectId.", examples=[examples.PROFILE_USER["id"]])
    username: str = Field(description="Normalized public handle without a leading @.", examples=[examples.PROFILE_USER["username"]])
    display_name: str = Field(description="Public name displayed on the profile card.", examples=[examples.PROFILE_USER["display_name"]])
    avatar_url: str | None = Field(description="Same-origin avatar URL, or null when no avatar is set.", examples=[examples.PROFILE_USER["avatar_url"]])
