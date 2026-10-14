import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


router = APIRouter(tags=["Media"])
ICON_DIRECTORY = Path(__file__).parent / "icons"


@router.get(
    "/static/images/badges/{icon_name}",
    response_class=FileResponse,
    summary="Read a static badge icon",
    description="Returns a bundled public badge icon without authentication or object storage access. Unknown icons return 404.",
)
async def read_badge_icon(icon_name: str) -> FileResponse:
    if not re.fullmatch(r"[a-zA-Z0-9_-]+\.(svg|png|webp)", icon_name):
        raise HTTPException(404, "Badge icon not found")
    path = ICON_DIRECTORY / icon_name
    if not path.is_file():
        raise HTTPException(404, "Badge icon not found")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"})
