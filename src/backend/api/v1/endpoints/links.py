from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from backend.api.metadata import Origin, Username, documented_responses
from backend.auth.dependencies import CurrentUser
from backend.auth.rate_limit import enforce_rate_limit
from backend.links.preview import LinkPreviewRequest, link_preview
from backend.links.resolution import LinkResolution, resolve_link
from backend.links.service import LinkService
from backend.profiles.repository import ProfileRepository
from backend.publications.attachments import OpenGraphAttachment

router = APIRouter()
service = LinkService()


@router.post(
    "/links/preview", response_model=OpenGraphAttachment,
    summary="Preview an external link", description="Fetch bounded public HTML and return a text-only card.",
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
) -> OpenGraphAttachment:
    """Return safe metadata for an authenticated publication editor.

    :param _origin: Required same-origin header.
    :param payload: Public link to preview.
    :param request: Request used for the account and IP rate limit.
    :param response: HTTP response for the private cache policy.
    :param current_user: Authenticated editor requesting the card.
    :return: Ready-to-store link attachment, with hostname fallback when unavailable.
    """
    await enforce_rate_limit(request, "link-preview", str(current_user.id), limit=20, window_seconds=60)
    response.headers["Cache-Control"] = "private, no-store"

    return await link_preview(payload.url)


@router.post(
    "/links/resolve", response_model=LinkResolution, tags=["Links"],
    summary="Resolve a link to a player or card",
    description="Confirm a concrete provider resource using bounded metadata; unsupported or unavailable resources become cards.",
    responses=documented_responses(401, 403, 422, 429, 503),
)
async def resolve_external_link(
    _origin: Origin, payload: LinkPreviewRequest, request: Request, current_user: CurrentUser,
) -> LinkResolution:
    """Resolve an editor URL without accepting iframe markup.

    :param _origin: Required same-origin mutation header.
    :param payload: Public URL to resolve.
    :param request: Request used for rate limiting.
    :param current_user: Authenticated editor.
    :return: Safe card or verified player presentation.
    """
    await enforce_rate_limit(request, "link-preview", str(current_user.id), limit=20, window_seconds=60)
    return await resolve_link(payload.url)


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
