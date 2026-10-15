"""OpenAPI presentation metadata for the Commonplace API reference."""

from copy import deepcopy
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from backend.core import api_examples as examples
from backend.core.config import get_settings


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


OPERATION_DOCS = {
    ("get", "/api/v1/auth/me"): ("Get the current account", "Returns the account associated with the current session cookie."),
    ("post", "/api/v1/auth/register"): ("Register and start a session", "Creates an account with a unique email and public username, then starts a session and sets the HttpOnly cookie. Returns 409 if the email or username is already taken. Limited to five attempts per hour per IP address and email."),
    ("post", "/api/v1/auth/login"): ("Log in", "Accepts an email address or username, optionally prefixed with @. Successful login sets the HttpOnly session cookie and returns the account. Limited to eight attempts per ten minutes per IP address and identifier."),
    ("post", "/api/v1/auth/logout"): ("Log out this session", "Revokes the current session and clears the cookie."),
    ("get", "/api/v1/auth/sessions"): ("List active sessions", "Returns your unrevoked, unexpired sessions, most recently active first. Includes the latest recorded IP address and User-Agent, absolute expiry, and a flag identifying the current session."),
    ("delete", "/api/v1/auth/sessions/{session_id}"): ("Revoke a session", "Revokes one of your sessions. Unknown and other users' sessions both return 404."),
    ("post", "/api/v1/auth/sessions/logout-others"): ("Log out other sessions", "Revokes every active session except the cookie used for this request."),
    ("get", "/api/v1/users/{username}"): ("Get a public profile", "Username is case-insensitive; follow state is relative to the optional current session."),
    ("get", "/api/v1/links/{link_id}/redirect"): ("Open a saved link", "Public 302 redirect to the saved HTTP(S) destination, independent of profile username, with Cache-Control: no-store. Removed or unknown IDs return 404; malformed UUIDs return 422. Destination queries and fragments are retained; endpoint query parameters are ignored. No UTM tagging or click counting is implemented yet."),
    ("get", "/api/v1/users/{username}/links/{link_id}/redirect"): ("Open a legacy profile link", "Deprecated compatibility alias. New links use /api/v1/links/{link_id}/redirect. Requires the ID to belong to the named profile; returns 302 with no-store, or 404."),
    ("get", "/api/v1/me/profile"): ("Get your own profile", "Returns your profile revision and all your badge assignments, including hidden ones, with assignment timestamps, preferences, and permissions. Requires your session; response uses private, no-store. Public profile responses never include these fields."),
    ("patch", "/api/v1/me/badges/{code}"): ("Change your badge visibility", "Send enabled and your expected profile revision. Requires your own assignment; unknown codes return 404, disabling a mandatory badge returns 403, and stale revisions or concurrent writes return 409. Returns your updated own profile and revision with private, no-store."),
    ("get", "/api/v1/users/{username}/publications"): ("List profile publications", "Returns up to 50 public micro-posts and published articles, newest first."),
    ("patch", "/api/v1/me/profile"): ("Update your profile", "Send the required revision from GET /me/profile; stale revisions and concurrent writes return 409. Omitted or null editable fields stay unchanged. Links replace the list (at most eight). Explicit IDs retain identity; entries without an ID reuse an unambiguous existing exact-URL match, otherwise get a new UUID. Duplicate, foreign, or ambiguous IDs return 422. Returns your updated own profile and revision with private, no-store. Badge visibility uses /me/badges/{code}."),
    ("get", "/api/v1/users/{username}/followers"): ("List followers", "Returns compact public profile cards."),
    ("get", "/api/v1/users/{username}/following"): ("List followed profiles", "Returns compact public profile cards."),
    ("put", "/api/v1/users/{username}/follow"): ("Follow a profile", "Idempotently creates a follow relationship; following yourself returns 400."),
    ("delete", "/api/v1/users/{username}/follow"): ("Unfollow a profile", "Idempotently removes the follow relationship."),
    ("post", "/api/v1/posts"): ("Publish a micro-post", "Creates a public post immediately. Text is trimmed and limited to 280 characters."),
    ("get", "/api/v1/posts/{post_id}"): ("Get a micro-post", "Returns a public post; deleted or malformed identifiers return 404."),
    ("patch", "/api/v1/posts/{post_id}"): ("Edit your micro-post", "Only the author may edit a post. The complete text field is required."),
    ("delete", "/api/v1/posts/{post_id}"): ("Delete your micro-post", "Soft-deletes the post; only the author may delete it."),
    ("post", "/api/v1/articles"): ("Create an article draft", "Creates a private-to-author draft. The body must follow the supported TipTap JSON schema."),
    ("get", "/api/v1/me/articles"): ("List your articles", "Returns your articles. Filter status by all, draft, scheduled, or published; defaults to all. Unpublished articles are visible only to their author."),
    ("get", "/api/v1/articles/{article_id}"): ("Get an article", "Returns the full TipTap body and media URLs. Published articles are public; drafts and scheduled articles require their author's session. Missing, deleted, inaccessible, and malformed IDs return 404."),
    ("patch", "/api/v1/articles/{article_id}"): ("Edit your article", "Partial update of title, summary, or TipTap JSON body; only the author may edit."),
    ("post", "/api/v1/articles/{article_id}/publish"): ("Publish an article now", "Makes your draft or scheduled article public immediately, assigns its publication timestamp, and clears the schedule. Publishing an already published article leaves its timestamp unchanged."),
    ("post", "/api/v1/articles/{article_id}/draft"): ("Return an article to draft", "Unpublishes or unschedules your article and makes it private to you."),
    ("post", "/api/v1/articles/{article_id}/schedule"): ("Schedule an article", "Sets a future timezone-aware publication time; the background worker publishes it automatically."),
    ("delete", "/api/v1/articles/{article_id}"): ("Delete an article", "Soft-deletes your draft, scheduled article, or publication."),
    ("get", "/api/v1/publications/{username}/{share_slug}"): ("Read a shared publication", "Resolves the UUID-safe slug in /@username/slug--share-id and returns the public post or article."),
    ("get", "/api/v1/feeds/public"): ("Read the public feed", "Chronological mixed feed of public micro-posts and published articles."),
    ("get", "/api/v1/feeds/following"): ("Read the following feed", "Chronological mixed feed from followed authors; requires a session cookie."),
    ("get", "/"): ("Identify the application", "Returns a short application identifier without checking dependency connectivity. Use /health to inspect service availability."),
    ("get", "/health"): ("Check dependency health", "Pings MongoDB and Redis and checks object storage; returns 503 if a dependency is unavailable."),
}

PROTECTED_OPERATIONS = {
    ("get", "/api/v1/auth/me"), ("post", "/api/v1/auth/logout"), ("get", "/api/v1/auth/sessions"),
    ("delete", "/api/v1/auth/sessions/{session_id}"), ("post", "/api/v1/auth/sessions/logout-others"),
    ("get", "/api/v1/me/profile"), ("patch", "/api/v1/me/profile"), ("patch", "/api/v1/me/badges/{code}"),
    ("put", "/api/v1/users/{username}/follow"), ("delete", "/api/v1/users/{username}/follow"),
    ("post", "/api/v1/posts"), ("patch", "/api/v1/posts/{post_id}"), ("delete", "/api/v1/posts/{post_id}"),
    ("post", "/api/v1/articles"), ("get", "/api/v1/me/articles"), ("patch", "/api/v1/articles/{article_id}"),
    ("post", "/api/v1/articles/{article_id}/publish"), ("get", "/api/v1/feeds/following"),
    ("post", "/api/v1/articles/{article_id}/draft"), ("post", "/api/v1/articles/{article_id}/schedule"),
    ("delete", "/api/v1/articles/{article_id}"),
}

PARAMETER_DOCS = {
    "code": ("Code of a badge assigned to your own profile; each code occurs at most once per profile.", examples.BADGE["code"]),
    "link_id": ("Stable link UUID returned in the profile's links array.", examples.LINK_RESPONSE["id"]),
    "icon_name": ("Bundled badge icon filename including its extension.", "star.svg"),
    "upload_id": ("Upload session ObjectId from the matching preparation endpoint; only its owner can confirm it.", "65f0c2a1b2c3d4e5f6071899"),
    "collection": ("Image category: avatars, post-images, article-covers, or article-images.", "post-images"),
    "username": ("Public handle of the profile or publication author; matching is case-insensitive.", examples.ACCOUNT["username"]),
    "session_id": ("Session ObjectId from the active session list. You can revoke only your own sessions.", examples.SESSION["id"]),
    "post_id": ("Micro-post ObjectId returned when the post was created.", examples.POST["id"]),
    "article_id": ("Article ObjectId returned when the draft was created.", examples.ARTICLE["id"]),
    "share_slug": ("Readable slug followed by -- and the publication's stable share UUID; take it from share_url after the author handle.", examples.ARTICLE["share_url"].rsplit("/", 1)[-1]),
    "kind": ("Publication type filter: all combines micro-posts and articles, micro_post returns only notes, and article returns only articles.", "all"),
    "status": ("Article state filter: all, draft, scheduled, or published. Applies to your own articles.", "all"),
    "cursor": ("Opaque next_cursor from the previous feed page. Omit for the first page; keep the same kind filter.", examples.CURSOR),
    "limit": ("Maximum publications per feed page, from 1 to 50. Defaults to 20.", 2),
}

RESPONSE_EXAMPLES = {
    ("get", "/"): [({"message": "FastAPI Microblog Demo"}, "Application identifier")],
    ("get", "/health"): [({"status": "ok", "database": "ok", "redis": "ok", "object_storage": "ok"}, "All dependencies available")],
    ("post", "/api/v1/posts"): [(examples.POST, "New public note")],
    ("post", "/api/v1/articles"): [(examples.ARTICLE, "New private draft")],
    ("post", "/api/v1/articles/{article_id}/publish"): [(examples.ARTICLE_PUBLISHED | {"thumbnail_url": None}, "Article published immediately")],
    ("post", "/api/v1/articles/{article_id}/draft"): [(examples.ARTICLE, "Private draft with no schedule")],
    ("post", "/api/v1/articles/{article_id}/schedule"): [(examples.ARTICLE_SCHEDULED, "Article awaiting scheduled publication")],
    ("patch", "/api/v1/articles/{article_id}"): [(examples.ARTICLE_UPDATED, "Updated private article")],
    ("get", "/api/v1/publications/{username}/{share_slug}"): [
        (examples.POST_WITH_IMAGES, "Public micro-post"),
        (examples.ARTICLE_PUBLISHED, "Published article"),
    ],
}


def _operation_tag(path: str) -> str:
    if path.startswith("/api/v1/links/") or "{link_id}" in path:
        return "Links"
    if path.startswith("/static/images/") or "/uploads" in path:
        return "Media"
    if path.startswith("/api/v1/auth/sessions"):
        return "Sessions"
    if path.startswith("/api/v1/auth/"):
        return "Authentication"
    if path.startswith("/api/v1/posts"):
        return "Micro-posts"
    if path.startswith("/api/v1/articles") or path == "/api/v1/me/articles":
        return "Articles"
    if path.startswith("/api/v1/publications/"):
        return "Publications"
    if path.startswith("/api/v1/feeds/"):
        return "Feeds"
    if path.startswith("/api/v1/users/") or path.startswith("/api/v1/me/"):
        return "Profiles"
    return "System"


def _schema_examples(node: dict, schemas: dict) -> list[Any]:
    """Read Pydantic examples, preserving alternatives and list response shapes."""
    if "$ref" in node:
        return _schema_examples(schemas.get(node["$ref"].rsplit("/", 1)[-1], {}), schemas)
    if node.get("examples"):
        return node["examples"]
    if node.get("type") == "array":
        items = _schema_examples(node.get("items", {}), schemas)
        return [[items[0]]] if items else []
    return [value for option in node.get("anyOf", node.get("oneOf", [])) for value in _schema_examples(option, schemas)]


def _named_examples(values: list[tuple[Any, str]]) -> dict:
    return {
        f"example_{index}": {
            "summary": f"{value['status'].capitalize()} article" if summary == "Example response" and isinstance(value, dict) and value.get("kind") == "article" and "status" in value else summary,
            "value": deepcopy(value),
        }
        for index, (value, summary) in enumerate(values, start=1)
    }


def _error_response(description: str, detail: str) -> dict:
    return {
        "description": description,
        "content": {"application/json": {
            "schema": {"type": "object", "required": ["detail"], "properties": {
                "detail": {"type": "string", "description": "Human-readable reason the request could not be completed.", "examples": [detail]},
            }},
            "examples": {"error": {"summary": description, "value": {"detail": detail}}},
        }},
    }


def _document_upload(operation: dict, path: str) -> None:
    if "/uploads" not in path:
        return
    completing = path.endswith("/complete")
    operation["description"] = (
        "Confirm all uploaded files, validate their actual size and image signatures, and attach immutable final objects. "
        "Requires the resource owner's session. Repeating a completed confirmation returns its saved result. "
        "A post confirmation replaces the complete gallery in request order; an article image confirmation appends one inline image."
        if completing else
        "Send JSON file metadata to receive ten-minute presigned PUT URLs. Upload each file's raw bytes using the returned headers, "
        "without application cookies, then call the matching completion endpoint. One file is required, except post galleries accept "
        "one to five files. JPEG, PNG, and WebP are accepted: 5 MiB per file, or 10 MiB for article covers. "
        "Creating an upload does not change the resource. Articles accept up to 30 inline images."
    )
    if completing and "/me/avatar/" in path:
        operation["description"] += (
            " Avatar attachment increments the profile revision once. Every confirmation response, including replay, "
            "returns the current own-profile schema with private badge settings and revision, using private, no-store."
        )
        operation["description"] = operation["description"].replace(
            "Repeating a completed confirmation returns its saved result.",
            "Repeating a completed confirmation does not attach the avatar again.",
        )
    operation["responses"].update({
        "413": _error_response("An image exceeds the configured size limit.", "Image exceeds the configured size limit"),
        "503": _error_response("Image storage or database is unavailable; retry the request.", "Image storage or database is unavailable"),
    })
    if completing:
        operation["responses"].update({
            "409": _error_response("The upload expired, files are missing, or confirmation conflicts with another operation.", "Upload all files before confirming"),
            "415": _error_response("Image bytes do not match a supported requested format.", "Use JPEG, PNG, or WebP bytes matching the requested content type"),
            "422": _error_response("The actual size differs from metadata or the article image limit was reached.", "Uploaded size does not match the requested size"),
        })


def configure_openapi(app: FastAPI) -> None:
    """Install cached OpenAPI generation with readable sections and complete examples."""
    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            summary=app.summary,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        components = schema.setdefault("components", {})
        schemas = components.setdefault("schemas", {})
        validation = schemas.get("ValidationError", {})
        validation["description"] = "One request validation issue. The location identifies the body, query, path, or header field."
        for name, description, value in (
            ("loc", "Path to the invalid or missing request field.", ["body", "password"]),
            ("msg", "Human-readable explanation of the validation failure.", "Field required"),
            ("type", "Machine-readable Pydantic validation error code.", "missing"),
        ):
            if name in validation.get("properties", {}):
                validation["properties"][name].update(description=description, examples=[value])
        validation_response = schemas.get("HTTPValidationError", {})
        validation_response["description"] = "The request failed validation; detail lists the affected fields."
        if "detail" in validation_response.get("properties", {}):
            validation_response["properties"]["detail"]["description"] = "Validation issues found in the request."
        components.setdefault("securitySchemes", {})["SessionCookie"] = {
            "type": "apiKey", "in": "cookie", "name": get_settings().session_cookie_name,
            "description": "HttpOnly session cookie issued by registration or login. Retain it in a cookie jar; browsers send it on same-origin requests.",
        }
        for path, path_item in schema.get("paths", {}).items():
            for method, operation in path_item.items():
                if method not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                    continue
                key = (method, path)
                if key in OPERATION_DOCS:
                    operation["summary"], operation["description"] = OPERATION_DOCS[key]
                operation["tags"] = [_operation_tag(path)]
                for parameter in operation.get("parameters", []):
                    details = PARAMETER_DOCS.get(parameter["name"])
                    if parameter["name"] == "object_name":
                        collection = path.split("/")[-2]
                        url = {"avatars": examples.AVATAR_URL, "post-images": examples.POST_IMAGE_URL,
                               "article-covers": examples.THUMBNAIL_URL, "article-images": examples.ARTICLE_IMAGE["url"]}.get(collection, examples.POST_IMAGE_URL)
                        details = ("Stored image filename, including its extension; take it from the returned media URL.", url.rsplit("/", 1)[-1])
                    if details:
                        parameter["description"], parameter["example"] = details
                if "/uploads" in path or key in PROTECTED_OPERATIONS:
                    operation["security"] = [{"SessionCookie": []}]
                    operation["responses"]["401"] = _error_response("A valid session cookie is required.", "Authentication required")
                if path.startswith("/static/images/") and not path.startswith("/static/images/badges/"):
                    operation["security"] = [{}, {"SessionCookie": []}]
                    operation["responses"]["503"] = _error_response("Image storage is unavailable.", "Image storage is unavailable")
                if "{" in path:
                    resource = (
                        "Session" if "{session_id}" in path else
                        "Post" if "{post_id}" in path else
                        "Article" if "{article_id}" in path else
                        "Link" if "{link_id}" in path else
                        "Badge assignment" if path.startswith("/api/v1/me/badges/") else
                        "Profile" if path.startswith("/api/v1/users/") else
                        "Badge icon" if "{icon_name}" in path else
                        "Publication" if path.startswith("/api/v1/publications/") else
                        "Avatar" if "/avatars/" in path else
                        "Thumbnail" if "/article-covers/" in path else "Image"
                    )
                    operation["responses"]["404"] = _error_response("The resource does not exist, was deleted, or is not accessible to this viewer.", f"{resource} not found")
                if key == ("put", "/api/v1/users/{username}/follow"):
                    operation["responses"]["400"] = _error_response("An account cannot follow itself.", "You cannot follow yourself")
                if key in {("patch", "/api/v1/me/profile"), ("patch", "/api/v1/me/badges/{code}")}:
                    operation["responses"]["409"] = _error_response("The profile revision is stale or a concurrent write occurred.", "Profile changed; reload your profile before saving")
                if key in {("get", "/api/v1/users/{username}"), ("get", "/api/v1/me/profile"),
                           ("patch", "/api/v1/me/profile"), ("patch", "/api/v1/me/badges/{code}")}:
                    operation["responses"]["503"] = _error_response("A referenced badge definition is missing.", "Badge definition is unavailable")
                if method in {"post", "put", "patch", "delete"} and path.startswith("/api/v1/"):
                    operation["responses"].setdefault("409", _error_response("A concurrent write conflicted; reload before retrying.", "The resource changed; reload before retrying"))
                    operation["responses"].setdefault("503", _error_response("Database unavailable; reload before retrying an uncertain write.", "Database is unavailable; reload before retrying"))
                    operation.setdefault("parameters", []).append({
                        "name": "Origin", "in": "header", "required": True,
                        "description": "Must match the configured application origin. Browsers set this header automatically.",
                        "schema": {"type": "string"}, "example": get_settings().app_origin,
                    })
                    operation["responses"]["403"] = _error_response("The Origin header is missing or does not match the application origin.", "Cross-origin request rejected")
                    if key == ("patch", "/api/v1/me/badges/{code}"):
                        operation["responses"]["403"] = _error_response("The Origin is invalid or this badge cannot be disabled.", "This badge cannot be disabled")
                request_content = operation.get("requestBody", {}).get("content", {}).get("application/json")
                if request_content:
                    values = _schema_examples(request_content.get("schema", {}), schemas)
                    if values:
                        request_content["examples"] = _named_examples([(value, "Example request") for value in values])
                _document_upload(operation, path)
                validation_content = operation.get("responses", {}).get("422", {}).get("content", {}).get("application/json")
                if validation_content:
                    body_content = operation.get("requestBody", {}).get("content", {})
                    body_schema = next((media["schema"] for media in body_content.values() if "schema" in media), {})
                    if "$ref" in body_schema:
                        body_schema = schemas.get(body_schema["$ref"].rsplit("/", 1)[-1], {})
                    required = body_schema.get("required", [])
                    if required:
                        validation_content["examples"] = _named_examples([({"detail": [{
                            "loc": ["body", required[0]], "msg": "Field required", "type": "missing",
                        }]}, "A required request field is missing")])
                    elif any(parameter["name"] == "limit" for parameter in operation.get("parameters", [])):
                        validation_content["examples"] = _named_examples([({"detail": [{
                            "loc": ["query", "limit"], "msg": "Input should be less than or equal to 50", "type": "less_than_equal",
                        }]}, "The requested page size exceeds 50")])
                for code, response in operation.get("responses", {}).items():
                    if code == "204":
                        response["description"] = "Completed successfully; no response body."
                    if not code.startswith("2") or code == "204":
                        continue
                    if path.startswith("/static/images/"):
                        response["description"] = "Image bytes in the detected format."
                        response["content"] = {
                            media_type: {"schema": {"type": "string", "format": "binary", "description": "Raw image bytes; save or display as an image."}}
                            for media_type in (("image/svg+xml", "image/png", "image/webp") if path.startswith("/static/images/badges/") else ("image/jpeg", "image/png", "image/webp"))
                        }
                        continue
                    content = response.get("content", {}).get("application/json")
                    if content is None:
                        continue
                    values = RESPONSE_EXAMPLES.get(key)
                    if values is None:
                        values = [(value, "Example response") for value in _schema_examples(content.get("schema", {}), schemas)]
                    if values:
                        content["examples"] = _named_examples(values)
                if path in {"/api/v1/auth/register", "/api/v1/auth/login"}:
                    operation["responses"]["429"] = _error_response("Too many authentication attempts; try again later.", "Too many attempts. Please try again later.")
                    operation["responses"]["503"] = _error_response("The authentication rate-limit service is unavailable.", "Authentication service is temporarily unavailable")
                if key == ("post", "/api/v1/auth/register"):
                    operation["responses"]["409"] = _error_response("The email address or username is already registered.", "Email or username is already in use")
                if key == ("post", "/api/v1/auth/login"):
                    operation["responses"]["401"] = _error_response("The supplied credentials are incorrect.", "Invalid username/email or password")
                if key == ("get", "/health"):
                    operation["responses"]["503"] = _error_response("A dependency check failed.", "A required service is unavailable")
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
