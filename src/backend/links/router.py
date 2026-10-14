from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from backend.links.service import LinkService
from backend.profiles.repository import ProfileRepository


router = APIRouter(tags=["Links"])
service = LinkService()


@router.get("/links/{link_id}/redirect", response_class=RedirectResponse, status_code=302,
            responses={302: {"description": "Temporary redirect to the saved destination.", "headers": {
                "Location": {"description": "Saved absolute HTTP(S) URL.", "schema": {"type": "string"}},
                "Cache-Control": {"schema": {"type": "string", "example": "no-store"}},
            }}})
async def redirect_link(link_id: UUID) -> RedirectResponse:
    destination = await service.destination(str(link_id))
    if destination is None:
        raise HTTPException(404, "Link not found")
    return RedirectResponse(destination, status_code=302, headers={"Cache-Control": "no-store"})


@router.get("/users/{username}/links/{link_id}/redirect", response_class=RedirectResponse, status_code=302,
            deprecated=True, summary="Open a legacy profile link",
            description="Compatibility alias for existing URLs. New clients use /links/{link_id}/redirect.")
async def redirect_legacy_profile_link(username: str, link_id: UUID) -> RedirectResponse:
    user = await ProfileRepository.find_by_username(username)
    if user is None or not any(link.id == str(link_id) for link in user.links):
        raise HTTPException(404, "Link not found")
    return await redirect_link(link_id)
