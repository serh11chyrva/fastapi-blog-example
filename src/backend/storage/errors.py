"""Image protocol failures with their documented HTTP status mapping."""

from backend.core.errors import ApplicationError


class ImageTooLarge(ApplicationError):
    status_code = 413


class UnsupportedImage(ApplicationError):
    status_code = 415
