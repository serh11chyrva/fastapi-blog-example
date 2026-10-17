"""Stable image paths shared by publication presenters and uploads."""

def publication_image_url(key: str, collection: str) -> str:
    """Build an API image path from a stored publication image key.

    :param key: Stored object key identifying the image.
    :param collection: Public image collection used in the API path.
    :return: The relative image URL for the requested collection.
    """
    return f"/static/images/{collection}/{key.rsplit('/', 1)[-1]}"
