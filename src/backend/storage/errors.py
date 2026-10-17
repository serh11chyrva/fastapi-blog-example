"""Image protocol failures with their documented HTTP status mapping."""

from backend.core.errors import ApplicationError


class ImageTooLarge(ApplicationError):
    """Image size rejection reported with HTTP status 413."""

    status_code = 413


class UnsupportedImage(ApplicationError):
    """Unsupported image format rejection reported with HTTP status 415."""

    status_code = 415
