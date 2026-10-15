"""Shared OpenAPI presentation; operation contracts live next to their routes."""

from copy import deepcopy
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


API_DESCRIPTION = """Publish short notes and long-form articles, discover writers, and manage your profile.

### Authentication and browser requests
Register or log in to receive an HttpOnly session cookie. Browsers send it automatically
on subsequent same-origin requests; API clients must retain it in a cookie jar.
Protected operations show the **SessionCookie** security requirement.
Every POST, PUT, PATCH, and DELETE request under `/api/v1` must include an `Origin`
header matching the configured application origin (`http://localhost:8080` by default).

### Publications and media
Micro-posts are public immediately. Articles start as private drafts and can be
published immediately, scheduled for a future time, or returned to draft.
Article bodies use TipTap JSON. Upload inline images to the article before referencing
their returned URLs in its body. Request upload URLs with JSON metadata, PUT raw bytes
to Garage without application cookies, then confirm the upload. URLs last ten minutes.
Image downloads use `/static/images/` and retain article access checks.

### Pagination and conventions
Feeds return newest-first pages. Pass `next_cursor` unchanged as the next request's
`cursor` and keep the same `kind` filter. A null cursor marks the end of the feed.
Document identifiers are MongoDB ObjectIds; profile links and publication shares use UUIDs.
Timestamps include a timezone and are returned in UTC. Media and share URLs are relative to this origin.
Partial updates leave omitted or null fields unchanged. Empty strings or lists clear fields where allowed.
Profile links use format version 1 and badges version 2. Open a link's redirect_url for a
temporary redirect; platform identifies its site. Public profiles include only visible badges.
GET /me/profile returns private badge settings and the revision required for profile writes.
Successful 204 responses have no body. Errors use `detail`; validation errors use a list of field issues.

Examples use fictional accounts and illustrative IDs. Create your own resources before
using their IDs in live requests, and choose a future time when scheduling an article.
"""

OPENAPI_TAGS = [
    {"name": "Links", "description": "Open saved HTTP(S) links through temporary redirects independent of profile handles. Query parameters are not forwarded; analytics is not implemented yet."},
    {"name": "Authentication", "description": "Create an account, sign in with an email or username, read your account, and sign out. Registration and login set the HttpOnly session cookie; logout revokes it."},
    {"name": "Sessions", "description": "Inspect your active browser sessions and their last activity. Revoke a selected session or sign out every other device while retaining the current session."},
    {"name": "Profiles", "description": "Browse public profiles and their publications, followers, and followed writers. Update your own biography, links, and avatar, or manage follow relationships."},
    {"name": "Micro-posts", "description": "Publish public notes of up to 280 characters. Authors can edit or delete their notes and replace their attachments with up to five images."},
    {"name": "Articles", "description": "Write TipTap articles as private drafts, add a cover and inline images, then publish or schedule them. Drafts and scheduled articles, including their media, are accessible only to their author."},
    {"name": "Publications", "description": "Resolve a public publication from its author handle and readable share slug with a stable UUID. Responses can contain either a micro-post or a published article."},
    {"name": "Feeds", "description": "Read public publications or publications from writers you follow, newest first. Filter by type and paginate with an opaque cursor; the following feed requires a session."},
    {"name": "Media", "description": "Prepare and confirm direct image uploads, and read JPEG, PNG, or WebP bytes. Avatars and post images are public; unpublished article media requires the author's session."},
    {"name": "System", "description": "Identify the application and inspect dependency availability. The health endpoint checks MongoDB, Redis, and object storage and returns 503 when a required service is unavailable."},
]

def _schema_examples(node: dict[str, Any], schemas: dict[str, Any]) -> list[Any]:
    """Read Pydantic examples, preserving alternatives and list response shapes."""
    if "$ref" in node:
        return _schema_examples(schemas.get(node["$ref"].rsplit("/", 1)[-1], {}), schemas)
    if node.get("examples"):
        return node["examples"]
    if node.get("type") == "array":
        items = _schema_examples(node.get("items", {}), schemas)
        return [[items[0]]] if items else []
    return [value for option in node.get("anyOf", node.get("oneOf", [])) for value in _schema_examples(option, schemas)]

def _named_examples(values: list[tuple[Any, str]]) -> dict[str, Any]:
    return {
        f"example_{index}": {
            "summary": f"{value['status'].capitalize()} article" if summary == "Example response" and isinstance(value, dict) and value.get("kind") == "article" and "status" in value else summary,
            "value": deepcopy(value),
        }
        for index, (value, summary) in enumerate(values, start=1)
    }


def configure_openapi(app: FastAPI) -> None:
    """Add schema-derived examples without inferring endpoint policy from URL text."""
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, summary=app.summary, description=app.description, routes=app.routes, tags=app.openapi_tags)
        schemas = schema.get("components", {}).get("schemas", {})
        for path_item in schema.get("paths", {}).values():
            for method, operation in path_item.items():
                if method not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                    continue
                request = operation.get("requestBody", {}).get("content", {}).get("application/json")
                if request is not None:
                    values = _schema_examples(request.get("schema", {}), schemas)
                    if values:
                        request.setdefault("examples", _named_examples([(value, "Example request") for value in values]))
                for code, response in operation.get("responses", {}).items():
                    if code == "204":
                        response["description"] = "Completed successfully; no response body."
                    if not code.startswith("2") or code == "204":
                        continue
                    content = response.get("content", {}).get("application/json")
                    if content is None:
                        continue
                    values = _schema_examples(content.get("schema", {}), schemas)
                    if values:
                        content.setdefault("examples", _named_examples([(value, "Example response") for value in values]))
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
