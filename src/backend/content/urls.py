import re


def share_url(username: str, title: str) -> str:
    """Build the readable author-and-title prefix; share_path appends the stable ID.

    :param username: Public profile handle, optionally prefixed with @.
    :param title: Publication title used to derive the readable URL slug.
    :return: The relative author and title path without a stable share ID.
    """
    from unicodedata import normalize

    value = normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", value).strip("-")[:64].strip("-") or "note"

    return f"/@{username}/{slug}"


def share_path(username: str, title: str, share_id: str) -> str:
    """Append the persisted share ID; resolution ignores the readable title slug.

    :param username: Public profile handle, optionally prefixed with @.
    :param title: Publication title used to derive the readable URL slug.
    :param share_id: Persisted stable share identity appended to the readable path.
    :return: The relative publication path including its stable share ID.
    """
    return f"{share_url(username, title)}--{share_id}"


def article_thumbnail_url(key: str | None) -> str | None:
    """Build the API image path for an optional article cover.

    :param key: Stored object key identifying the image.
    :return: The relative cover URL, or None when no cover exists.
    """
    if not key:
        return None

    return f"/static/images/article-covers/{key.rsplit('/', 1)[-1]}"


def publication_image_url(key: str, collection: str) -> str:
    """Build an API image path from a stored publication image key.

    :param key: Stored object key identifying the image.
    :param collection: Public image collection used in the API path.
    :return: The relative image URL for the requested collection.
    """
    return f"/static/images/{collection}/{key.rsplit('/', 1)[-1]}"
