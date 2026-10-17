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
