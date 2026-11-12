from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.api import examples
from backend.articles.validation import ArticleBody, validate_tiptap_document
from backend.links.schemas import LinkPresentation
from backend.profiles.schemas import ProfileUserResponse
from backend.publications.attachments import PublicationAttachment, PublicationAttachments
from backend.publications.state import PublicationState


class ArticleCreate(BaseModel):
    """Article draft whose body is a validated TipTap JSON document."""

    model_config = ConfigDict(
        title="New article draft", extra="forbid",
        json_schema_extra={"examples": [examples.ARTICLE_CREATE, examples.ARTICLE_RICH_CREATE]},
    )

    attachments: PublicationAttachments = Field(
        default_factory=list,
        description="Up to 30 ordered typed attachments. Referenced articles must be published. "
        "Images must be uploaded to this article; video is reserved and rejected.",
    )
    title: str = Field(
        min_length=1,
        max_length=160,
        description="Article title, trimmed and nonblank, up to 160 characters.",
        examples=[examples.ARTICLE_CREATE["title"]],
    )
    body: ArticleBody = Field(
        description=(
            "TipTap JSON document, up to 1,000,000 UTF-8 bytes, 64 levels, and 10,000 nodes. Malformed node shapes "
            "and parent-child structures are rejected. Supports paragraphs, headings (levels 1-3), lists, blockquotes, "
            "code blocks, breaks, rules, uploaded images, inline mention/hashtag nodes, and block attachment nodes "
            "(typed descriptors in attrs, up to 30 per body); marks: bold, italic, strike, code, and HTTP(S) links. "
            "Image sources must reference images uploaded to this article. Mention and article references are checked "
            "on writes; video is reserved and rejected."
        ),
        examples=[examples.ARTICLE_BODY, examples.ARTICLE_RICH_CREATE["body"]],
    )

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        """Trim an article title and reject an empty supplied value.

        :param value: Article title to trim and require to be nonblank when supplied.
        :return: The trimmed nonempty article title.
        """
        value = value.strip()

        if not value:
            raise ValueError("Title cannot be empty")

        return value

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: ArticleBody) -> ArticleBody:
        """Validate a supplied TipTap body without replacing its JSON structure.

        :param value: TipTap JSON body supplied when creating the draft.
        :return: The original validated TipTap document.
        """
        validate_tiptap_document(value)

        return value


class ArticleUpdate(BaseModel):
    """Partial article update. The author can edit drafts and publications."""

    model_config = ConfigDict(
        title="Article changes", extra="forbid",
        json_schema_extra={"examples": [examples.ARTICLE_UPDATE]},
    )

    attachments: PublicationAttachments | None = Field(
        default=None,
        description="Replacement attachments. Omit or use null to preserve; [] clears explicit descriptors. "
        "Uploaded images remain in the image inventory.",
    )
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=160,
        description="Replacement title, trimmed and nonblank. Omit or use null to keep the current title.",
        examples=[examples.ARTICLE_UPDATE["title"]],
    )
    body: ArticleBody | None = Field(
        default=None,
        description="Complete replacement TipTap JSON document, subject to the same rules as creation. Omit or use null to keep the body. Referenced images must have been uploaded to this article.",
        examples=[examples.ARTICLE_BODY, examples.ARTICLE_RICH_CREATE["body"]],
    )

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str | None) -> str | None:
        """Trim an article title and reject an empty supplied value.

        :param value: Article title to trim and require to be nonblank when supplied.
        :return: The trimmed title, preserving None for partial updates.
        """
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Title cannot be empty")

        return value

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: ArticleBody | None) -> ArticleBody | None:
        """Validate a supplied TipTap body without replacing its JSON structure.

        :param value: TipTap JSON body to validate, or None for an omitted update.
        :return: The original validated document, or None for an omitted update.
        """
        if value is not None:
            validate_tiptap_document(value)

        return value


class ArticleScheduleRequest(BaseModel):
    """Timezone-aware timestamp when an article should become public."""

    model_config = ConfigDict(
        title="Article publication schedule",
        json_schema_extra={"examples": [examples.ARTICLE_SCHEDULE]},
    )

    publish_at: datetime = Field(
        description="Future publication time with a timezone (Z or an explicit offset). Converted to UTC; past or timezone-naive values are rejected.",
        examples=[examples.PUBLISH_AT],
    )

    @field_validator("publish_at")
    @classmethod
    def require_future_utc_time(cls, value: datetime) -> datetime:
        """Reject naive or past publication times and normalize to UTC.

        :param value: Requested publication timestamp including a timezone.
        :return: The future timezone-aware publication timestamp in UTC.
        """
        if value.tzinfo is None:
            raise ValueError("Publish time must include a timezone")

        value = value.astimezone(UTC)

        if value <= datetime.now(UTC):
            raise ValueError("Publish time must be in the future")

        return value


class ArticleResponse(LinkPresentation, PublicationState):
    """Full article data. Drafts, scheduled articles, and archives are visible only to their owner."""

    model_config = ConfigDict(
        title="Article",
        json_schema_extra={
            "examples": [
                examples.ARTICLE_PUBLISHED,
                examples.ARTICLE,
                examples.ARTICLE_WITH_FEATURED_AUTHORS,
                examples.ARTICLE_WITH_CONTENT,
                examples.ARTICLE_ARCHIVED,
            ]
        },
    )

    id: str = Field(
        description="Article identifier: a 24-character MongoDB ObjectId.",
        examples=[examples.ARTICLE["id"]],
    )
    kind: Literal["article"] = Field(
        default="article",
        description="Publication type; always article.",
        examples=["article"],
    )
    share_url: str | None = Field(
        default=None,
        description="Relative page URL with a readable slug and stable UUID. The article is publicly accessible only when published.",
        examples=[examples.ARTICLE["share_url"]],
    )
    attachments: list[PublicationAttachment] = Field(
        default_factory=list,
        description="Ordered typed descriptors followed by inline images without explicit placement. "
        "Resolve referenced IDs through normal endpoints; their availability can change.",
    )
    title: str = Field(
        description="Article title without surrounding whitespace.",
        examples=[examples.ARTICLE_CREATE["title"]],
    )
    summary: str = Field(
        max_length=280,
        description="Read-only first 280 characters of normalized article body text; may be empty.",
        examples=[examples.ARTICLE["summary"]],
    )
    body: ArticleBody = Field(
        description="Validated TipTap JSON document used to render the full article.",
        examples=[examples.ARTICLE_BODY, examples.ARTICLE_RICH_CREATE["body"]],
    )
    thumbnail_url: str | None = Field(
        default=None,
        description="Same-origin cover image URL, or null when absent. Unpublished media requires the owner's session.",
        examples=[examples.THUMBNAIL_URL],
    )
    inline_image_urls: list[str] = Field(
        default_factory=list,
        description="URLs of images uploaded to this article, including images not yet inserted into its body. Up to 30 images.",
        examples=[[examples.ARTICLE_IMAGE["url"]]],
    )
    status: Literal["draft", "scheduled", "published"] = Field(
        description="Visibility state: draft and scheduled are private to the owner; published is public.",
        examples=["published", "draft", "scheduled"],
    )
    owner_id: str = Field(
        description="Account owning the publication and controlling edits, uploads, and private visibility.",
        examples=[examples.ACCOUNT["id"]],
    )
    authors: list[ProfileUserResponse] = Field(
        min_length=1,
        description=(
            "Public author cards: owner first, then featured authors in stored order. "
            "Featured authors receive no ownership or private-access rights."
        ),
        examples=[[examples.AUTHOR]],
    )
    created_at: datetime = Field(
        description="UTC time when the draft was created.",
        examples=[examples.ARTICLE["created_at"]],
    )
    updated_at: datetime = Field(
        description="UTC time of the most recent content, media, or publication-state update.",
        examples=[examples.ARTICLE_PUBLISHED["updated_at"]],
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Planned UTC publication time while scheduled; null when draft or published.",
        examples=[examples.PUBLISH_AT, None],
    )
    published_at: datetime | None = Field(
        description="UTC time when the article became public; null while draft or scheduled.",
        examples=[examples.ARTICLE_PUBLISHED["published_at"], None],
    )


class ArticleImageResponse(BaseModel):
    """Uploaded inline image metadata for insertion into an article's TipTap body."""

    model_config = ConfigDict(
        title="Uploaded article image",
        json_schema_extra={"examples": [examples.ARTICLE_IMAGE]},
    )

    url: str = Field(
        description="Same-origin image URL. Use this value as attrs.src in a TipTap image node for this article.",
        examples=[examples.ARTICLE_IMAGE["url"]],
    )
    alt_text: str = Field(
        description="Suggested alternate text, taken from the original filename; replace it with a useful image description in the editor.",
        examples=[examples.ARTICLE_IMAGE["alt_text"]],
    )
