import re


def share_url(username: str, title: str) -> str:
    """Build the readable author-and-title prefix; share_path appends the stable ID."""
    from unicodedata import normalize

    value = normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", value).strip("-")[:64].strip("-") or "note"
    return f"/@{username}/{slug}"


def share_path(username: str, title: str, share_id: str) -> str:
    """Append the persisted share ID; resolution ignores the readable title slug."""
    return f"{share_url(username, title)}--{share_id}"


def article_thumbnail_url(key: str | None) -> str | None:
    if not key:
        return None
    return f"/static/images/article-covers/{key.rsplit('/', 1)[-1]}"


def publication_image_url(key: str, collection: str) -> str:
    return f"/static/images/{collection}/{key.rsplit('/', 1)[-1]}"
