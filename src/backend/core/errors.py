"""Application failures translated to HTTP only at the application boundary."""


class ApplicationError(Exception):
    status_code = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFound(ApplicationError):
    status_code = 404


class InvalidOperation(ApplicationError):
    status_code = 422


class Conflict(ApplicationError):
    status_code = 409


class Forbidden(ApplicationError):
    status_code = 403


class Unavailable(ApplicationError):
    status_code = 503
