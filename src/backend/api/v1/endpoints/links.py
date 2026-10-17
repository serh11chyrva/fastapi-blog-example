from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from backend.api.metadata import documented_responses, Username
from backend.links.service import LinkService
from backend.profiles.repository import ProfileRepository


router = APIRouter()
service = LinkService()


@router.get(
    "/links/{link_id}/redirect",
    response_class=RedirectResponse,
    status_code=302,
    responses={**documented_responses(404, 503), **{302: {"description": "Temporary redirect to the saved destination.", "headers": {
                "Location": {"description": "Saved absolute HTTP(S) URL.", "schema": {"type": "string"}},
                "Cache-Control": {"schema": {"type": "string", "example": "no-store"}},
            }}}},
    summary='Open a saved link',
    description=(
        'Public 302 redirect to the saved HTTP(S) destination, independent of profile '
        'username, with Cache-Control: no-store. Removed or unknown IDs return 404; malformed '
        'UUIDs return 422. Destination queries and fragments are retained; endpoint query '
        'parameters are ignored. No UTM tagging or click counting is implemented yet.'
    ),
    tags=['Links'],
)
async def redirect_link(link_id: UUID) -> RedirectResponse:
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
    tags=['Links'],
    responses=documented_responses(404, 503),
)
async def redirect_legacy_profile_link(username: Username, link_id: UUID) -> RedirectResponse:
    user = await ProfileRepository.find_by_username(username)
    if user is None or not any(link.id == str(link_id) for link in user.links):
        raise HTTPException(404, "Link not found")
    return await redirect_link(link_id)
