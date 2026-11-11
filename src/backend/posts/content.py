"""Short-publication content rules shared by writes and image confirmation."""

from backend.core.errors import InvalidOperation
from backend.publications.attachments import ImageAttachment, PublicationAttachment
from backend.storage.urls import publication_image_url


def retained_image_keys(image_keys: list[str], retained_urls: list[str] | None) -> list[str]:
    """Select owned gallery images in the requested order without mutating the inventory.

    :param image_keys: Stored image keys owned by the post or its private upload draft.
    :param retained_urls: Public image URLs to keep; None preserves all and an empty list removes all.
    :return: Selected keys; duplicate or foreign URLs raise InvalidOperation.
    """
    if retained_urls is None:
        return list(image_keys)
    inventory = {publication_image_url(key, "post-images"): key for key in image_keys}
    if len(set(retained_urls)) != len(retained_urls) or any(url not in inventory for url in retained_urls):
        raise InvalidOperation("Retained images must belong to this post")
    return [inventory[url] for url in retained_urls]


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
