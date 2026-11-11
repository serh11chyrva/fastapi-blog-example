"""Short-publication content rules shared by writes and image confirmation."""

from backend.core.errors import InvalidOperation
from backend.publications.attachments import ImageAttachment, PublicationAttachment


def validate_post_content(text: str, attachments: list[PublicationAttachment], image_keys: list[str]) -> None:
    """Require content and a single attachment choice in the final saved state.

    :param text: Trimmed post or reply text, with at most 280 characters.
    :param attachments: Explicit typed descriptors belonging to the post.
    :param image_keys: Owned gallery image keys in display order.
    :return: None; invalid content raises InvalidOperation.
    """
    if len(text) > 280:
        raise InvalidOperation("Post text cannot exceed 280 characters")
    images = [item for item in attachments if isinstance(item, ImageAttachment)]
    other = [item for item in attachments if not isinstance(item, ImageAttachment)]
    if len(image_keys) > 5 or len(images) > 5:
        raise InvalidOperation("A gallery can contain up to five images")
    if len(other) > 1 or (other and (images or image_keys)):
        raise InvalidOperation("Choose one gallery, player, link card, or publication")
    if any(item.type not in {"og_card", "embed", "article", "post", "link"} for item in other):
        raise InvalidOperation("This attachment type is not supported in posts")
    if not text.strip() and not attachments and not image_keys:
        raise InvalidOperation("Add text or an attachment before publishing")
