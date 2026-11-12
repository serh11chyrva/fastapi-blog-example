from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.api import examples
from backend.links.models import LinkData
from backend.links.platforms import LinkPlatform
from backend.profiles.models import BadgePayload


class LinkInput(LinkData):
    """A public profile link. Only HTTP and HTTPS URLs are accepted."""

    model_config = ConfigDict(title="Profile link input", json_schema_extra={"examples": [examples.LINK]})

    id: UUID | None = Field(
        default=None,
        description="Existing UUID to preserve identity; must belong to your profile. Without an ID, an unambiguous exact-URL match is reused; otherwise a new ID is generated.",
    )


class LinkResponse(BaseModel):
    """Public saved link including platform detection and a stable redirect URL."""

    model_config = ConfigDict(title="Profile link", json_schema_extra={"examples": [examples.LINK_RESPONSE]})

    version: Literal[1] = Field(description="Link format version.", examples=[1])
    id: UUID = Field(description="Stable link UUID; retain it in updates to keep the redirect URL.")
    label: str = Field(description="Short public label for the link.")
    url: str = Field(description="Original absolute HTTP(S) destination URL.")
    platform: LinkPlatform = Field(
        description="Server-detected platform for future frontend icons; website means an unrecognized domain."
    )
    redirect_url: str = Field(
        description="Same-origin API URL to open in the browser; returns a temporary 302 redirect to the saved destination."
    )


class ProfileUpdate(BaseModel):
    """Partial profile update. Omitted fields are left unchanged."""

    model_config = ConfigDict(
        extra="forbid",
        title="Profile changes",
        json_schema_extra={"examples": [examples.PROFILE_UPDATE]},
    )
    revision: int = Field(
        ge=0,
        description="Expected revision from GET /me/profile. A stale revision returns 409; this is separate from format version.",
        examples=[0],
    )

    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="Replacement public name, trimmed and nonblank. Unicode hashtags are searchable and linked. "
        "Omit or use null to keep the current value.",
        examples=[examples.ACCOUNT["display_name"]],
    )
    bio: str | None = Field(
        default=None,
        max_length=280,
        description="Replacement biography with searchable Unicode hashtags. Use an empty string to clear it; "
        "omit or use null to leave it unchanged.",
        examples=[examples.PROFILE_UPDATE["bio"]],
    )
    location: str | None = Field(
        default=None,
        max_length=80,
        description="Public location. Send an empty string to clear it, or omit it to keep the current value.",
    )

    links: list[LinkInput] | None = Field(
        default=None,
        max_length=8,
        description="Replacement list of up to eight public links. Use [] to clear links; omit or use null to keep them.",
        examples=[[examples.LINK]],
    )

    @field_validator("location")
    @classmethod
    def trim_location(cls, value: str | None) -> str | None:
        """Trim a public location while preserving an omitted update.

        :param value: Optional public location supplied by the owner.
        :return: Trimmed location, or None for an omitted update.
        """
        return value.strip() if value is not None else None

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str | None) -> str | None:
        """Trim a public display name and reject blank input.

        :param value: Public display name to trim, or None for an omitted update.
        :return: The trimmed display name, preserving None for partial updates.
        """
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Display name cannot be empty")

        return value


class BadgeResponse(BaseModel):
    """A badge assigned to a profile in the demo."""

    model_config = ConfigDict(title="Profile badge", json_schema_extra={"examples": [examples.BADGE]})

    version: Literal[2] = Field(
        description="Badge format version; version 2 puts all display fields in payload.",
        examples=[2],
    )
    payload: BadgePayload = Field(description="Public display payload: label, description, colors, and icon.")

    code: str = Field(description="Machine-readable badge code.", examples=[examples.BADGE["code"]])


class BadgePreferences(BaseModel):
    """Private owner-controlled badge display preferences."""

    enabled: bool = Field(description="Owner-selected public visibility.")


class BadgePermissions(BaseModel):
    """Catalog policy describing the badge controls available to its owner."""

    can_disable: bool = Field(description="Server-enforced permission to hide this badge.")


class OwnerBadgeResponse(BadgeResponse):
    """Assigned badge including private preferences and allowed controls."""

    model_config = ConfigDict(
        title="Own badge assignment",
        json_schema_extra={"examples": [examples.OWNER_BADGE]},
    )
    assigned_at: datetime = Field(description="Private UTC assignment timestamp.")
    preferences: BadgePreferences = Field(description="Private visibility preferences for this assignment.")
    permissions: BadgePermissions = Field(description="Private capabilities enforced by the server.")


class BadgePreferenceUpdate(BaseModel):
    """Revision-checked request to change an assigned badge visibility."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"revision": 0, "enabled": False}]},
    )
    revision: int = Field(ge=0, description="Expected own-profile revision; stale updates return 409.")
    enabled: bool = Field(description="Desired visibility. Disabling a mandatory badge returns 403.")


class AvatarResponse(BaseModel):
    """Available avatar variants, currently limited to the original uploaded image."""

    original: str | None = Field(
        description="Same-origin original avatar URL, or null when no avatar is set.",
        examples=[examples.AVATAR_URL, None],
    )


class ProfileResponse(BaseModel):
    """A public profile, with follow state relative to the requesting viewer."""

    model_config = ConfigDict(title="Public profile", json_schema_extra={"examples": [examples.PROFILE]})

    id: str = Field(
        description="Account identifier: a 24-character MongoDB ObjectId.",
        examples=[examples.ACCOUNT["id"]],
    )
    username: str = Field(
        description="Normalized public handle without a leading @.",
        examples=[examples.ACCOUNT["username"]],
    )
    display_name: str = Field(
        description="Public name displayed on the profile.",
        examples=[examples.ACCOUNT["display_name"]],
    )
    bio: str = Field(
        description="Public biography; an empty string means none was provided.",
        examples=[examples.PROFILE["bio"]],
    )
    links: list[LinkResponse] = Field(
        description="Versioned public links in the order chosen by the profile owner; open redirect_url for navigation.",
        examples=[[examples.LINK_RESPONSE]],
    )
    avatars: AvatarResponse = Field(
        description="Available avatar variants; original is null when no avatar is set.",
        examples=[{"original": examples.AVATAR_URL}],
    )
    badges: list[BadgeResponse] = Field(
        description="Only publicly visible badges. Owner settings and assignment timestamps are never included.",
        examples=[[examples.BADGE]],
    )
    joined_at: datetime | None = Field(default=None, description="Public account creation timestamp.")
    location: str = Field(default="", description="Public location, or an empty string.")
    posts_count: int = Field(default=0, ge=0, description="Number of public posts crediting this account.")
    banner_url: str | None = Field(default=None, description="Public profile banner image, if configured.")
    follower_count: int = Field(description="Number of accounts following this profile.", examples=[127])
    following_count: int = Field(description="Number of accounts this profile follows.", examples=[43])
    is_following: bool = Field(
        description="Whether the current viewer follows this profile; false for anonymous viewers.",
        examples=[False],
    )


class OwnProfileResponse(ProfileResponse):
    """Owner profile including private badge controls and the current revision."""

    model_config = ConfigDict(title="Own profile", json_schema_extra={"examples": [examples.OWN_PROFILE]})
    revision: int = Field(description="Current profile revision to send with profile or badge preference updates.")
    badges: list[OwnerBadgeResponse] = Field(
        description="All your assignments, including hidden badges, with private settings."
    )


class ProfileUserResponse(BaseModel):
    """Compact public profile card used by authors, follower lists, and following lists."""

    model_config = ConfigDict(
        title="Public profile card",
        json_schema_extra={"examples": [examples.PROFILE_USER]},
    )

    id: str = Field(
        description="Account identifier: a 24-character MongoDB ObjectId.",
        examples=[examples.PROFILE_USER["id"]],
    )
    username: str = Field(
        description="Normalized public handle without a leading @.",
        examples=[examples.PROFILE_USER["username"]],
    )
    display_name: str = Field(
        description="Public name displayed on the profile card; Unicode hashtags link to exact-tag search.",
        examples=[examples.PROFILE_USER["display_name"]],
    )
    avatars: AvatarResponse = Field(
        description="Available avatar variants; original is null when no avatar is set.",
        examples=[{"original": examples.AVATAR_URL}],
    )
