"""Read-only cached link presentations shared by publication response models."""

from pydantic import BaseModel, Field

from backend.links.resolution import LinkResolution


class LinkPresentation(BaseModel):
    """Expose response-only metadata without changing saved attachment descriptors."""

    link_resolutions: dict[str, LinkResolution] = Field(
        default_factory=dict,
        description="Read-only cached link presentations keyed by normalized URL. Missing metadata is queued, "
        "never fetched from external sites in this request. Empty when no supported external links are present.",
        json_schema_extra={"readOnly": True},
    )
