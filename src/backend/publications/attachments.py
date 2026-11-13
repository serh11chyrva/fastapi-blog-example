"""Shared, discriminated publication attachment contracts without executable markup."""

from __future__ import annotations

from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from backend.links.platforms import validate_link_url
from backend.publications.hashtags import validate_tag

type ContentUrl = Annotated[str, Field(max_length=2048), AfterValidator(validate_link_url)]
type ContentId = Annotated[str, Field(pattern=r"^[0-9a-fA-F]{24}$")]


class AttachmentBase(BaseModel):
    """Reject unknown attachment fields instead of storing arbitrary HTML or JSON."""

    model_config = ConfigDict(extra="forbid", strict=True)


class ImageAttachment(AttachmentBase):
    """Reference an image already uploaded to the containing publication."""

    type: Literal["image"] = "image"
    url: str = Field(
        pattern=r"^/static/images/(?:post-images|article-images)/[0-9a-f]{32}\.(?:jpg|png|webp)$",
        description="Same-origin JPEG, PNG, or WebP URL uploaded to this publication; ownership is checked on writes.",
    )
    alt: str = Field(default="", max_length=1000)


class GifAttachment(AttachmentBase):
    """Reference an uploaded GIF, preserving its animation independently of image galleries."""

    type: Literal["gif"] = "gif"
    url: str = Field(
        pattern=r"^/static/images/(?:post-images|article-images)/[0-9a-f]{32}\.gif$",
        description="Owned GIF URL; posts and comments allow one GIF without any other attachments.",
    )
    alt: str = Field(default="", max_length=1000)


class LinkAttachment(AttachmentBase):
    """Store a plain external link and an optional human-readable label."""

    type: Literal["link"] = "link"
    url: ContentUrl
    label: str | None = Field(default=None, min_length=1, max_length=200)


class MentionAttachment(AttachmentBase):
    """Identify a mentioned account independently of its mutable username."""

    type: Literal["mention"] = "mention"
    user_id: ContentId


class HashtagAttachment(AttachmentBase):
    """Store a Unicode hashtag without a leading hash or whitespace."""

    type: Literal["hashtag"] = "hashtag"
    tag: Annotated[str, AfterValidator(validate_tag)] = Field(
        min_length=1, max_length=64,
        description="Unicode letters, numbers, combining marks, or underscores, without #; exact search ignores case.",
    )


class OpenGraphAttachment(AttachmentBase):
    """Store caller-supplied preview metadata without fetching the destination."""

    type: Literal["og_card"] = "og_card"
    url: ContentUrl
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=1000)
    image_url: ContentUrl | None = None
    site_name: str | None = Field(default=None, min_length=1, max_length=200)


class ArticleAttachment(AttachmentBase):
    """Reference a published article without copying its private or mutable body."""

    type: Literal["article"] = "article"
    article_id: ContentId


class PostAttachment(AttachmentBase):
    """Reference an original public micro-post without storing its content."""

    type: Literal["post"] = "post"
    post_id: ContentId


class EmbedAttachment(AttachmentBase):
    """Describe a provider resource for a future client-side player integration."""

    type: Literal["embed"] = "embed"
    provider: Literal["soundcloud", "spotify", "youtube", "twitch", "vimeo"]
    url: ContentUrl = Field(description="HTTPS provider resource URL; arbitrary iframe HTML is not accepted.")

    @model_validator(mode="after")
    def validate_provider_url(self) -> EmbedAttachment:
        """Require HTTPS and an exact supported provider hostname.

        :return: The validated embed descriptor; no remote content is fetched.
        """
        parsed = urlsplit(self.url)
        domains = {
            "soundcloud": {"soundcloud.com", "www.soundcloud.com", "w.soundcloud.com"},
            "spotify": {"open.spotify.com"},
            "youtube": {"youtube.com", "www.youtube.com", "youtu.be", "www.youtube-nocookie.com"},
            "vimeo": {"vimeo.com", "www.vimeo.com", "player.vimeo.com"},
            "twitch": {"twitch.tv", "www.twitch.tv", "clips.twitch.tv", "player.twitch.tv"},
        }

        if parsed.scheme != "https" or parsed.hostname not in domains[self.provider] or parsed.port not in {None, 443}:
            raise ValueError("Embed URLs must use HTTPS and a supported hostname matching the provider")

        return self


class VideoAttachment(AttachmentBase):
    """Reserve the video discriminator for a future upload and playback implementation."""

    type: Literal["video"] = "video"
    url: ContentUrl


type PublicationAttachment = Annotated[
    ImageAttachment
    | GifAttachment
    | LinkAttachment
    | MentionAttachment
    | HashtagAttachment
    | OpenGraphAttachment
    | ArticleAttachment
    | PostAttachment
    | EmbedAttachment
    | VideoAttachment,
    Field(discriminator="type"),
]
type PublicationAttachments = Annotated[list[PublicationAttachment], Field(max_length=30)]


def display_attachments(attachments: list[PublicationAttachment], image_urls: list[str]) -> list[PublicationAttachment]:
    """Append uploaded images and GIF missing from the explicitly ordered attachment list.

    :param attachments: Stored ordered descriptors, including optional image or GIF placement and alternate text.
    :param image_urls: Current image and GIF inventory belonging to the publication.
    :return: Descriptors followed by unplaced files, using type gif for GIF URLs and type image otherwise.
    """
    placed = {item.url for item in attachments if isinstance(item, (ImageAttachment, GifAttachment))}

    return [
        *attachments,
        *(
            GifAttachment(url=url) if url.endswith(".gif") else ImageAttachment(url=url)
            for url in image_urls
            if url not in placed
        ),
    ]
