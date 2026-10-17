def article_thumbnail_url(key: str | None) -> str | None:
    """Build the API image path for an optional article cover.

    :param key: Stored object key identifying the image.
    :return: The relative cover URL, or None when no cover exists.
    """
    if not key:
        return None

    return f"/static/images/article-covers/{key.rsplit('/', 1)[-1]}"
