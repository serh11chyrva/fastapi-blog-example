"""Application failures translated to HTTP only at the application boundary."""


class ApplicationError(Exception):
    """Domain failure carrying a public detail and HTTP status code."""

    status_code = 500

    def __init__(self, detail: str) -> None:
        """Initialize a domain error with its public response detail.

        :param detail: Public error detail returned to API clients.
        :return: None.
        """
        super().__init__(detail)
        self.detail = detail


class NotFound(ApplicationError):
    """Missing or inaccessible resource reported with HTTP status 404."""

    status_code = 404


class BadRequest(ApplicationError):
    """Invalid request operation reported with HTTP status 400."""

    status_code = 400


class InvalidOperation(ApplicationError):
    """Rejected domain input reported with HTTP status 422."""

    status_code = 422


class Conflict(ApplicationError):
    """Uniqueness, revision, or concurrent write conflict reported with status 409."""

    status_code = 409


class Forbidden(ApplicationError):
    """Disallowed operation reported with HTTP status 403."""

    status_code = 403


class Unavailable(ApplicationError):
    """Unavailable infrastructure dependency reported with HTTP status 503."""

    status_code = 503
