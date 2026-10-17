"""Reusable OpenAPI response shapes and HTTP header annotations."""

from copy import deepcopy
from typing import Annotated, Any

from fastapi import Header, Path

Origin = Annotated[
    str,
    Header(
        alias="Origin",
        description="Must match APP_ORIGIN. Browsers set it automatically; missing or foreign origins are rejected with 403 before dispatch.",
    ),
]

PostId = Annotated[str, Path(description="Post ObjectId returned by the creation endpoint.")]
ArticleId = Annotated[str, Path(description="Article ObjectId returned when the draft was created.")]
SessionId = Annotated[
    str,
    Path(description="Session ObjectId from your active-session list; this is not the cookie token."),
]
UploadId = Annotated[
    str,
    Path(description="Upload session ObjectId from the matching preparation endpoint."),
]
Username = Annotated[
    str,
    Path(description="Public handle, matched case-insensitively, optionally prefixed with @."),
]
ShareSlug = Annotated[
    str,
    Path(description="Readable title followed by -- and the stable 32-character share ID; take it from share_url."),
]

ERRORS = {
    400: (
        "The operation is not allowed for this resource.",
        "You cannot follow yourself",
    ),
    401: ("A valid session cookie is required.", "Authentication required"),
    403: (
        "The Origin is invalid or the operation is forbidden.",
        "Cross-origin request rejected",
    ),
    404: ("The resource is missing, deleted, or inaccessible.", "Resource not found"),
    409: (
        "A revision, uniqueness, state, or concurrent write conflict occurred; reload before retrying.",
        "The resource changed; reload before retrying",
    ),
    413: (
        "An image exceeds the configured size limit.",
        "Image exceeds the configured size limit",
    ),
    415: (
        "Image bytes disagree with a supported requested format.",
        "Use JPEG, PNG, or WebP bytes matching the requested content type",
    ),
    422: (
        "Request validation or an application input rule failed.",
        "Uploaded size does not match the requested size",
    ),
    429: (
        "Too many authentication attempts; try again later.",
        "Too many attempts. Please try again later.",
    ),
    503: (
        "A dependency is unavailable. Reload before retrying an uncertain write.",
        "Database is unavailable; reload before retrying",
    ),
}


def documented_responses(
    *codes: int,
    examples: list[tuple[Any, str]] | None = None,
    success_status: int = 200,
) -> dict[int, dict[str, Any]]:
    """Declare endpoint errors and examples next to the endpoint itself.

    :param examples: Optional successful response values and their summaries.
    :param success_status: HTTP status under which successful examples are documented.
    :param codes: HTTP error status codes to document.
    :return: OpenAPI response descriptions and examples indexed by HTTP status.
    """
    responses: dict[int, dict[str, Any]] = {}

    for code in codes:
        description, detail = ERRORS[code]
        detail_schema: dict[str, Any] = {"type": "string"}

        if code == 422:
            detail_schema = {
                "anyOf": [
                    detail_schema,
                    {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "loc": {
                                    "type": "array",
                                    "items": {
                                        "anyOf": [
                                            {"type": "string"},
                                            {"type": "integer"},
                                        ]
                                    },
                                },
                                "msg": {"type": "string"},
                                "type": {"type": "string"},
                            },
                        },
                    },
                ]
            }

        responses[code] = {
            "description": description,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["detail"],
                        "properties": {"detail": detail_schema},
                    },
                    "examples": {"error": {"summary": description, "value": {"detail": detail}}},
                }
            },
        }

    if examples:
        responses[success_status] = {
            "content": {
                "application/json": {
                    "examples": {
                        f"example_{index}": {
                            "summary": summary,
                            "value": deepcopy(value),
                        }
                        for index, (value, summary) in enumerate(examples, start=1)
                    }
                }
            }
        }

    return responses
