from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, Query
from fastapi.responses import RedirectResponse

from backend.api.metadata import Origin, Username, documented_responses
from backend.auth.dependencies import CurrentUser, OptionalUser
from backend.auth.rate_limit import enforce_rate_limit
from backend.links.preview import LinkPreviewRequest
from backend.links.resolution import LinkResolution
from backend.links.cache import cached_resolution
from backend.core.resources import Resources
from backend.links.service import LinkService
from backend.profiles.repository import ProfileRepository
from backend.publications.attachments import OpenGraphAttachment

router = APIRouter()
service = LinkService()


@router.post(
    "/links/preview", response_model=OpenGraphAttachment,
    summary="Preview an external link", description="Read cached card metadata and queue a background refresh on a cache miss.",
    tags=["Links"],
    responses=documented_responses(
        401, 403, 422, 429, 503,
        examples=[({
            "type": "og_card", "url": "https://example.com/", "title": "Example Domain",
            "description": "", "site_name": "example.com", "image_url": None,
        }, "Link preview")],
    ),
)
async def preview_link(
    _origin: Origin, payload: LinkPreviewRequest, request: Request, response: Response, current_user: CurrentUser,
    resources: Resources,
) -> OpenGraphAttachment:
    """Return safe metadata for an authenticated publication editor.

    :param _origin: Required same-origin header.
    :param payload: Public link to preview.
    :param request: Request used for the account and IP rate limit.
    :param response: HTTP response for the private cache policy.
    :param current_user: Authenticated editor requesting the card.
    :param resources: Application cache infrastructure.
    :return: Ready-to-store link attachment, with hostname fallback when unavailable.
    """
    await enforce_rate_limit(request, "link-preview", str(current_user.id), limit=20, window_seconds=60)
    response.headers["Cache-Control"] = "private, no-store"

    return (await cached_resolution(resources.redis, payload.url)).card


@router.post(
    "/links/resolve", response_model=LinkResolution, tags=["Links"],
    summary="Resolve a link to a player or card",
    description="Read cached provider metadata or return a pending card while a worker resolves the URL.",
    responses=documented_responses(401, 403, 422, 429, 503),
)
async def resolve_external_link(
    _origin: Origin, payload: LinkPreviewRequest, request: Request, current_user: CurrentUser, resources: Resources,
) -> LinkResolution:
    """Resolve an editor URL without accepting iframe markup.

    :param _origin: Required same-origin mutation header.
    :param payload: Public URL to resolve.
    :param request: Request used for rate limiting.
    :param current_user: Authenticated editor.
    :param resources: Application cache infrastructure.
    :return: Cached card/player or a pending hostname fallback.
    """
    await enforce_rate_limit(request, "link-preview", str(current_user.id), limit=20, window_seconds=60)
    return await cached_resolution(resources.redis, payload.url)


@router.get(
    "/links/resolved", response_model=LinkResolution, tags=["Links"],
    summary="Read cached external link metadata",
    description="Returns cached metadata without fetching the destination in the request. Cache misses queue background work.",
    responses=documented_responses(422, 429, 503),
)
async def read_resolved_link(
    request: Request, response: Response, resources: Resources, current_user: OptionalUser,
    url: str = Query(max_length=2048),
) -> LinkResolution:
    """Read a cached presentation for authenticated or anonymous publication readers.

    :param request: Incoming request used for rate limits.
    :param response: Response receiving a cache policy.
    :param resources: Application Redis infrastructure.
    :param current_user: Optional current account for rate-limit isolation.
    :param url: Public URL whose metadata is requested.
    :return: Cached player/card or a pending fallback.
    """
    await enforce_rate_limit(request, "link-read", str(current_user.id) if current_user else "anonymous", limit=240, window_seconds=60)
    response.headers["Cache-Control"] = "no-store"
    return await cached_resolution(resources.redis, url)


@router.get(
    "/links/{link_id}/redirect",
    response_class=RedirectResponse,
    status_code=302,
    responses={
        **documented_responses(404, 503),
        **{
            302: {
                "description": "Temporary redirect to the saved destination.",
                "headers": {
                    "Location": {
                        "description": "Saved absolute HTTP(S) URL.",
                        "schema": {"type": "string"},
                    },
                    "Cache-Control": {"schema": {"type": "string", "example": "no-store"}},
                },
            }
        },
    },
    summary="Open a saved link",
    description=(
        "Public 302 redirect to the saved HTTP(S) destination, independent of profile "
        "username, with Cache-Control: no-store. Removed or unknown IDs return 404; malformed "
        "UUIDs return 422. Destination queries and fragments are retained; endpoint query "
        "parameters are ignored. No UTM tagging or click counting is implemented yet."
    ),
    tags=["Links"],
)
async def redirect_link(link_id: UUID) -> RedirectResponse:
    """Resolve a saved link identity to its current destination.

    :param link_id: Stable identity of the saved profile link.
    :return: A temporary redirect to the saved HTTP or HTTPS URL.
    """
    destination = await service.destination(str(link_id))

    if destination is None:
        raise HTTPException(404, "Link not found")

    return RedirectResponse(destination, status_code=302, headers={"Cache-Control": "no-store"})


@router.get(
    "/users/{username}/links/{link_id}/redirect",
    response_class=RedirectResponse,
    status_code=302,
    deprecated=True,
    summary="Open a legacy profile link",
    description="Compatibility alias for existing URLs. New clients use /links/{link_id}/redirect.",
    tags=["Links"],
    responses=documented_responses(404, 503),
)
async def redirect_legacy_profile_link(username: Username, link_id: UUID) -> RedirectResponse:
    """Resolve a saved link through its legacy profile-specific route.

    :param username: Public profile handle, optionally prefixed with @.
    :param link_id: Stable identity of the saved profile link.
    :return: A temporary redirect to the saved destination.
    """
    user = await ProfileRepository.find_by_username(username)

    if user is None or not any(link.id == str(link_id) for link in user.links):
        raise HTTPException(404, "Link not found")

    return await redirect_link(link_id)
