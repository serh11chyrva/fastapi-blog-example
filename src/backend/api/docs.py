"""Shared OpenAPI presentation; operation contracts live next to their routes."""

from copy import deepcopy
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from scalar_fastapi import AgentScalarConfig, Theme, add_scalar_reference

API_TITLE = "FastAPI Blog Example API"
API_VERSION = "0.1.0"
API_SUMMARY = "A session-based microblog and article publishing API."
OPENAPI_URL = "/api/openapi.json"
API_REFERENCE_URL = "/api/docs"

API_DESCRIPTION = """Publish short notes and long-form articles, discover writers, and manage your profile.

### Authentication and browser requests
Register or log in to receive an HttpOnly session cookie. Browsers send it automatically
on subsequent same-origin requests; API clients must retain it in a cookie jar.
Protected operations show the **SessionCookie** security requirement.
Every POST, PUT, PATCH, and DELETE request under `/api/v1` must include an `Origin`
header matching `APP_ORIGIN` (`http://localhost:8080` by default) or the optional
`APP_ADDITIONAL_ORIGIN`.
Registration and login accept `client_type`: `web` (default), `mobile`, or `desktop`.
Native apps may supply a `device_name` and must also retain the cookie and send `Origin`.
Session lists return readable location and browser/device labels instead of raw IP and User-Agent.

### Publications and media
Micro-posts are public immediately. Articles start as private drafts and can be
published immediately, scheduled for a future time, or returned to draft.
Article bodies use TipTap JSON. Upload inline images to the article before referencing
their returned URLs in its body. Request upload URLs with JSON metadata, PUT raw bytes
to Garage without application cookies, then confirm the upload. URLs last ten minutes.
Image downloads use `/static/images/` and retain article access checks.
Posts and articles accept ordered `attachments` discriminated by `type`: image, link, mention,
hashtag, og_card, article, post, and embed. Video is reserved and currently returns 422.
Up to 30 explicit descriptors are accepted; responses append uploaded images without explicit placement.
Post images are represented only as `type: image` elements in `attachments`; there is no separate `images` field.
Image references must belong to the publication, mentioned accounts must exist, and newly
referenced publications must be public. Article bodies support inline mention/hashtag nodes and
block attachment nodes (up to 30 descriptors per body). The authenticated link preview endpoint
can return cached OG metadata. Confirmed players load near the viewport without media autoplay.
Publication responses also expose optional read-only `link_resolutions`, a map from normalized
external URLs to cached `status`, `card`, `attachment`, and `player_url` data. This includes originals
inside reposts, saves, and discussion entries, and links in article body blocks. Responses batch
Redis reads after visibility checks and feed-cache reads; missing data queues background work.
External destinations are never fetched during publication reads. Saved attachment descriptors
and article bodies are unchanged; clients may ignore the new field or treat its absence as `{}`.
Original publication responses and feed items expose a nonempty `authors` array of public profile cards,
with the owner first, followed by featured authors in stored order. Responses also expose `owner_id`.
Only the owner controls edits and private access; featured authors are display credits. Creation leaves
featured authors empty. Featured-author management and collaboration permissions are not implemented.
Profiles and author cards expose `avatars: {"original": URL-or-null}`. The object is always present;
only the original uploaded image is available today. These replace flat author fields and avatar URLs.

### Interactions and discussions
Use PUT or DELETE on a publication's `/like` or `/save` endpoint to set an idempotent account state.
Post-only `/repost` endpoints create or remove public repost events without quotation text.
Reposts appear in public/following feeds as `kind: repost`, with `reposted_by`, repost `published_at`,
and an original `post` object. Following feeds select reposts by the followed reposter, even when
the original author is not followed. kind=micro_post includes reposts; kind=article excludes them.
Original feed publications expose their own `published_at` and, when available, `updated_at`.
GET `/posts/{id}/interactions` or `/articles/{id}/interactions` returns live counts and optional
viewer flags. Save totals and other accounts' saves are private; GET `/me/saved` returns only yours.
Viewer-state and saved-list responses use Cache-Control: private, no-store and never enter public feed caches.
GET `/profiles/{username}/reposts` returns public repost history. The profile timeline at
`/users/{username}/timeline` merges public posts, reposts, and authored comments with article cards.
Comment events carry their own `created_at` and `updated_at`.
Post discussions use `/posts/{id}/replies`, with optional parent_id and immutable root_id/depth.
Read roots first, then request each parent's direct children with bounded pagination at any depth.
Article `/articles/{id}/comments` are flat and reject parent_id. Both accept trimmed plain text up
to 5,000 characters. Only the comment author may edit or delete. Deleted entries retain a tombstone
with null text/author, preserving children. New replies require a live parent in the same post.
Live entries support idempotent likes, optional viewer flags, and ranked pages.
Interactions and discussion reads/creates require public originals; drafts and scheduled articles
return 404 even to their owner. Interaction removal remains available for inaccessible originals.
All mutations require a session and Origin and commit audit events in the same transaction.

### Pagination and conventions
Feeds return newest-first pages. Pass `next_cursor` unchanged as the next request's
`cursor` and keep the same `kind` filter. A null cursor marks the end of the feed.
Document identifiers are MongoDB ObjectIds; profile links and publication shares use UUIDs.
Timestamps include a timezone and are returned in UTC. Media and share URLs are relative to this origin.
Article partial updates leave omitted or null fields unchanged. Post edits require text and preserve omitted attachments; null attachments are invalid. Empty strings or lists clear fields where allowed.
Profile links use format version 1 and badges version 2. Open a link's redirect_url for a
temporary redirect; platform identifies its site. Public profiles include only visible badges.
GET /me/profile returns private badge settings and the revision required for profile writes.
Successful 204 responses have no body. Errors use `detail`; validation errors use a list of field issues.

Examples use fictional accounts and illustrative IDs. Create your own resources before
using their IDs in live requests, and choose a future time when scheduling an article.
"""

OPENAPI_TAGS = [
    {
        "name": "Links",
        "description": "Open saved HTTP(S) links through temporary redirects independent of profile handles. Query parameters are not forwarded; analytics is not implemented yet.",
    },
    {
        "name": "Authentication",
        "description": "Create an account, sign in with an email or username, read your account, and sign out. Registration and login set the HttpOnly session cookie; logout revokes it.",
    },
    {
        "name": "Sessions",
        "description": "Inspect active web, mobile, and desktop sessions with approximate locations, readable browser/device labels, and last activity. Revoke a selected session or sign out every other device while retaining the current session.",
    },
    {
        "name": "Profiles",
        "description": "Browse public profiles and their publications, followers, and followed writers. Update your own biography, links, and avatar, or manage follow relationships.",
    },
    {
        "name": "Micro-posts",
        "description": "Publish public notes of up to 280 characters. Owners can edit or delete their notes, attach typed content, and upload up to five images.",
    },
    {
        "name": "Articles",
        "description": "Write TipTap articles as private drafts, add a cover, inline images, typed attachments, mentions, and hashtags, then publish or schedule them. Drafts and scheduled articles, including their media, are accessible only to their owner.",
    },
    {
        "name": "Publications",
        "description": "Resolve a public publication from its owner handle and readable share slug with a stable UUID. Responses can contain either a micro-post or a published article.",
    },
    {
        "name": "Feeds",
        "description": "Read public publications or publications from writers you follow, newest first. Filter by type and paginate with an opaque cursor; the following feed requires a session.",
    },
    {
        "name": "Media",
        "description": "Prepare and confirm direct image uploads, and read JPEG, PNG, or WebP bytes. Avatars and post images are public; unpublished article media requires the owner's session.",
    },
    {
        "name": "Interactions",
        "description": (
            "Like or privately save posts and published articles. Repost posts into public and following feeds. "
            "Read public counts, your private flags, your saved list, and public account repost histories."
        ),
    },
    {
        "name": "Comments",
        "description": (
            "Discuss posts through threaded replies or articles through flat comments. "
            "Like live entries and sort article comments or highlighted root replies by rank. "
            "Authors may edit and erase their own text; legacy reads retain navigation tombstones."
        ),
    },
    {
        "name": "System",
        "description": "Identify the application and inspect dependency availability. The health endpoint checks MongoDB, Redis, and object storage and returns 503 when a required service is unavailable.",
    },
]


def add_api_reference(app: FastAPI, *, documentation_only: bool = False) -> None:
    """Use the same reference presentation for the API and standalone preview.

    :param app: FastAPI application receiving configuration or lifecycle resources.
    :param documentation_only: Whether to hide live request controls in the reference
        preview.
    :return: None.
    """
    add_scalar_reference(
        app,
        route=API_REFERENCE_URL,
        title="API Reference — FastAPI Blog Example",
        theme=Theme.DEFAULT,
        order_schema_properties_by="preserve",
        order_required_properties_first=False,
        hide_models=not documentation_only,
        hide_test_request_button=documentation_only,
        hide_client_button=documentation_only,
        agent=AgentScalarConfig(disabled=True),
        telemetry=False,
    )


def _schema_examples(node: dict[str, Any], schemas: dict[str, Any]) -> list[Any]:
    """Read Pydantic examples, preserving alternatives and list response shapes.

    :param node: Schema node or document fragment to process.
    :param schemas: OpenAPI component schemas indexed by their model names.
    :return: Example values matching the resolved schema shape.
    """
    if "$ref" in node:
        return _schema_examples(schemas.get(node["$ref"].rsplit("/", 1)[-1], {}), schemas)

    if node.get("examples"):
        return node["examples"]

    if node.get("type") == "array":
        items = _schema_examples(node.get("items", {}), schemas)

        return [[items[0]]] if items else []

    return [value for option in node.get("anyOf", node.get("oneOf", [])) for value in _schema_examples(option, schemas)]


def _named_examples(values: list[tuple[Any, str]]) -> dict[str, Any]:
    """Copy example values into named OpenAPI example entries.

    :param values: Example values paired with their display summaries.
    :return: Example entries keyed by their one-based index.
    """
    return {
        f"example_{index}": {
            "summary": f"{value['status'].capitalize()} article"
            if summary == "Example response"
            and isinstance(value, dict)
            and value.get("kind") == "article"
            and "status" in value
            else summary,
            "value": deepcopy(value),
        }
        for index, (value, summary) in enumerate(values, start=1)
    }


def _order_example(value: Any, node: dict[str, Any], schemas: dict[str, Any]) -> Any:
    """Restore schema field order after Pydantic sorts example dictionaries.

    :param value: Example data whose fields should follow the schema order.
    :param node: Schema node or document fragment to process.
    :param schemas: OpenAPI component schemas indexed by their model names.
    :return: Example data with object fields ordered like the schema.
    """
    if "$ref" in node:
        node = schemas.get(node["$ref"].rsplit("/", 1)[-1], {})

    alternatives = node.get("oneOf", node.get("anyOf", []))

    if alternatives:
        if isinstance(value, dict):
            candidates = [
                schemas.get(option["$ref"].rsplit("/", 1)[-1], {}) if "$ref" in option else option
                for option in alternatives
            ]
            candidates = [
                option
                for option in candidates
                if option.get("type") != "null"
                and all(
                    value[key] == field["const"]
                    for key, field in option.get("properties", {}).items()
                    if key in value and "const" in field
                )
            ]

            if candidates:
                node = max(
                    candidates,
                    key=lambda option: len(value.keys() & option.get("properties", {}).keys()),
                )
        elif isinstance(value, list):
            node = next((option for option in alternatives if option.get("type") == "array"), {})

    if isinstance(value, list):
        return [_order_example(item, node.get("items", {}), schemas) for item in value]

    if isinstance(value, dict):
        properties = node.get("properties", {})
        additional = node.get("additionalProperties", {})
        additional = additional if isinstance(additional, dict) else {}
        keys = [key for key in properties if key in value]
        keys.extend(key for key in value if key not in properties)

        return {key: _order_example(value[key], properties.get(key, additional), schemas) for key in keys}

    return value


def _order_document_examples(node: Any, schemas: dict[str, Any]) -> None:
    """Align schema, parameter, and media examples without traversing example data.

    :param node: Schema node or document fragment to process.
    :param schemas: OpenAPI component schemas indexed by their model names.
    :return: None.
    """
    if isinstance(node, list):
        for item in node:
            _order_document_examples(item, schemas)
    elif isinstance(node, dict):
        example_schema = node.get("schema", node)

        if "example" in node:
            node["example"] = _order_example(node["example"], example_schema, schemas)

        examples = node.get("examples")

        if isinstance(examples, list):
            node["examples"] = [_order_example(value, example_schema, schemas) for value in examples]
        elif isinstance(examples, dict):
            for example in examples.values():
                if isinstance(example, dict) and "value" in example:
                    example["value"] = _order_example(example["value"], example_schema, schemas)

        for key, child in node.items():
            if key not in {"example", "examples", "default", "enum", "const"}:
                _order_document_examples(child, schemas)


def configure_openapi(app: FastAPI) -> None:
    """Add schema-derived examples and align their fields with the schema order.

    :param app: FastAPI application receiving configuration or lifecycle resources.
    :return: None.
    """

    def custom_openapi() -> dict[str, Any]:
        """Build and cache the application schema with ordered examples.

        :return: The cached or newly generated OpenAPI document.
        """
        if app.openapi_schema is not None:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            summary=app.summary,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        schemas = schema.get("components", {}).get("schemas", {})

        for path_item in schema.get("paths", {}).values():
            for method, operation in path_item.items():
                if method not in {
                    "get",
                    "post",
                    "put",
                    "patch",
                    "delete",
                    "head",
                    "options",
                }:
                    continue

                request = operation.get("requestBody", {}).get("content", {}).get("application/json")

                if request is not None:
                    values = _schema_examples(request.get("schema", {}), schemas)

                    if values:
                        request.setdefault(
                            "examples",
                            _named_examples([(value, "Example request") for value in values]),
                        )

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
                        content.setdefault(
                            "examples",
                            _named_examples([(value, "Example response") for value in values]),
                        )

        _order_document_examples(schema, schemas)
        app.openapi_schema = schema

        return schema

    app.openapi = custom_openapi
