"""Short-publication content rules shared by writes and image confirmation."""

from backend.core.errors import InvalidOperation
from backend.publications.attachments import GifAttachment, ImageAttachment, PublicationAttachment
from backend.storage.urls import publication_image_url


def retained_image_keys(image_keys: list[str], retained_urls: list[str] | None) -> list[str]:
    """Select owned images or GIF in the requested order without mutating the inventory.

    :param image_keys: Stored image or GIF keys owned by the post or its private upload draft.
    :param retained_urls: Public media URLs to keep; None preserves all and an empty list removes all.
    :return: Selected keys; duplicate or foreign URLs raise InvalidOperation.
    """
    if retained_urls is None:
        return list(image_keys)
    inventory = {publication_image_url(key, "post-images"): key for key in image_keys}
    if len(set(retained_urls)) != len(retained_urls) or any(url not in inventory for url in retained_urls):
        raise InvalidOperation("Retained images must belong to this post")
    return [inventory[url] for url in retained_urls]


def validate_post_content(text: str, attachments: list[PublicationAttachment], image_keys: list[str]) -> None:
    """Require content and one gallery, one exclusive GIF, or one other attachment.

    Invalid final content raises InvalidOperation before the caller commits the mutation.

    :param text: Trimmed post or reply text, with at most 280 characters.
    :param attachments: Explicit typed descriptors belonging to the post.
    :param image_keys: Owned image or GIF keys in display order, including implicitly placed files.
    :return: None.
    """
    if len(text) > 280:
        raise InvalidOperation("Post text cannot exceed 280 characters")

    images = [item for item in attachments if isinstance(item, ImageAttachment)]
    gifs = [item for item in attachments if isinstance(item, GifAttachment)]
    other = [item for item in attachments if not isinstance(item, (ImageAttachment, GifAttachment))]
    gif_keys = [key for key in image_keys if key.endswith(".gif")]

    if gifs or gif_keys:
        gif_urls = {item.url for item in gifs} | {publication_image_url(key, "post-images") for key in gif_keys}
        if len(gifs) > 1 or len(gif_keys) > 1 or len(gif_urls) > 1:
            raise InvalidOperation("A post or comment can contain only one GIF")
        if images or other or len(gif_keys) != len(image_keys):
            raise InvalidOperation("A GIF cannot be combined with images or other attachments in posts and comments")

    if len(image_keys) > 5 or len(images) > 5:
        raise InvalidOperation("A gallery can contain up to five images")

    if len(other) > 1 or (other and (images or image_keys)):
        raise InvalidOperation("Choose one gallery, GIF, player, link card, or publication")

    if any(item.type not in {"og_card", "embed", "article", "post", "link"} for item in other):
        raise InvalidOperation("This attachment type is not supported in posts")

    if not text.strip() and not attachments and not image_keys:
        raise InvalidOperation("Add text or an attachment before publishing")
